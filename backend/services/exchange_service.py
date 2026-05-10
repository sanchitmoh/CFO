import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import ExchangeRate

logger = logging.getLogger(__name__)

FRANKFURTER_API_URL = "https://api.frankfurter.app/latest"

class ExchangeService:
    @staticmethod
    async def get_exchange_rate(session: AsyncSession, from_currency: str, to_currency: str) -> Decimal:
        """
        Get the exchange rate to convert from `from_currency` to `to_currency`.
        Returns a Decimal representing the multiplier.
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        if from_currency == to_currency:
            return Decimal("1.0")

        # Check the database for a recent rate (e.g., from today)
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(ExchangeRate).where(
            ExchangeRate.base_currency == from_currency,
            ExchangeRate.target_currency == to_currency,
            ExchangeRate.date >= today
        ).order_by(ExchangeRate.date.desc()).limit(1)
        
        result = await session.execute(stmt)
        rate_record = result.scalar_one_or_none()
        
        if rate_record:
            return rate_record.rate
            
        # Try the inverse rate
        stmt_inverse = select(ExchangeRate).where(
            ExchangeRate.base_currency == to_currency,
            ExchangeRate.target_currency == from_currency,
            ExchangeRate.date >= today
        ).order_by(ExchangeRate.date.desc()).limit(1)
        
        result_inverse = await session.execute(stmt_inverse)
        inverse_record = result_inverse.scalar_one_or_none()
        
        if inverse_record:
            rate = Decimal("1.0") / inverse_record.rate
            # Cache this direction as well
            new_rate = ExchangeRate(
                base_currency=from_currency,
                target_currency=to_currency,
                rate=rate,
                date=datetime.now(timezone.utc)
            )
            session.add(new_rate)
            await session.commit()
            return rate

        # Fetch from API
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{FRANKFURTER_API_URL}?from={from_currency}&to={to_currency}")
                response.raise_for_status()
                data = response.json()
                rate_float = data.get("rates", {}).get(to_currency)
                
                if rate_float:
                    rate = Decimal(str(rate_float))
                    new_rate = ExchangeRate(
                        base_currency=from_currency,
                        target_currency=to_currency,
                        rate=rate,
                        date=datetime.now(timezone.utc)
                    )
                    session.add(new_rate)
                    await session.commit()
                    return rate
                else:
                    logger.warning(f"Could not find rate for {to_currency} in response: {data}")
        except Exception as e:
            logger.error(f"Error fetching exchange rate from API: {e}")
            
        # Fallback to an older rate if available
        stmt_old = select(ExchangeRate).where(
            ExchangeRate.base_currency == from_currency,
            ExchangeRate.target_currency == to_currency
        ).order_by(ExchangeRate.date.desc()).limit(1)
        result_old = await session.execute(stmt_old)
        old_record = result_old.scalar_one_or_none()
        if old_record:
            return old_record.rate
            
        # If all else fails, return 1.0
        logger.warning(f"Using fallback rate of 1.0 for {from_currency} to {to_currency}")
        return Decimal("1.0")

    @staticmethod
    async def convert_amount(session: AsyncSession, amount: Decimal, from_currency: str, to_currency: str) -> tuple[Decimal, Decimal]:
        """
        Converts an amount from one currency to another.
        Returns a tuple of (converted_amount, applied_exchange_rate).
        """
        rate = await ExchangeService.get_exchange_rate(session, from_currency, to_currency)
        converted = amount * rate
        return converted, rate
