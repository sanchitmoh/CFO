import httpx
import logging
from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import Optional, Dict
import traceback

from models import ExchangeRate

logger = logging.getLogger(__name__)

class ExchangeRateService:
    BASE_URL = "https://api.frankfurter.app"

    @classmethod
    async def get_exchange_rate(
        cls,
        db: AsyncSession,
        base_currency: str,
        target_currency: str,
        target_date: Optional[date] = None
    ) -> Decimal:
        """
        Get the exchange rate between two currencies.
        If they are the same, return 1.0.
        Uses local database caching. Falls back to Frankfurter API if not found.
        """
        base_currency = base_currency.upper()
        target_currency = target_currency.upper()
        
        if base_currency == target_currency:
            return Decimal("1.000000")

        # If no date is provided, use today's date
        if target_date is None:
            target_date = datetime.now(timezone.utc).date()

        # 1. Check local DB cache
        rate_record = await cls._get_from_db(db, base_currency, target_currency, target_date)
        if rate_record:
            return rate_record.rate

        # 2. If not found, check the reverse in DB (1 / rate)
        reverse_rate_record = await cls._get_from_db(db, target_currency, base_currency, target_date)
        if reverse_rate_record and reverse_rate_record.rate > 0:
            inverse_rate = Decimal("1.000000") / reverse_rate_record.rate
            # Cache the inverse rate to speed up future lookups
            await cls._save_to_db(db, base_currency, target_currency, inverse_rate, target_date)
            return inverse_rate

        # 3. Fetch from Frankfurter API
        try:
            fetched_rate = await cls._fetch_from_api(base_currency, target_currency, target_date)
            
            # Save to DB
            if fetched_rate is not None:
                await cls._save_to_db(db, base_currency, target_currency, fetched_rate, target_date)
                return fetched_rate
        except Exception as e:
            logger.error(f"Error fetching exchange rate from API: {str(e)}\n{traceback.format_exc()}")
            
        # 4. Fallback (If API fails, maybe try to find the closest date in DB, but for now just return 1.0 or raise an error)
        # To avoid blocking transactions on API downtime, returning a fallback or raising.
        # It's better to log a warning and return 1.0 if we really can't get it, or we could raise an exception.
        # We will raise a ValueError so the caller knows the conversion failed.
        raise ValueError(f"Could not fetch exchange rate for {base_currency} to {target_currency} on {target_date}")


    @classmethod
    async def _get_from_db(
        cls, 
        db: AsyncSession, 
        base_currency: str, 
        target_currency: str, 
        target_date: date
    ) -> Optional[ExchangeRate]:
        dt = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        stmt = select(ExchangeRate).where(
            ExchangeRate.base_currency == base_currency,
            ExchangeRate.target_currency == target_currency,
            ExchangeRate.date == dt
        )
        result = await db.execute(stmt)
        return result.scalars().first()


    @classmethod
    async def _save_to_db(
        cls,
        db: AsyncSession,
        base_currency: str,
        target_currency: str,
        rate: Decimal,
        target_date: date
    ) -> None:
        dt = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        new_rate = ExchangeRate(
            base_currency=base_currency,
            target_currency=target_currency,
            rate=rate,
            date=dt
        )
        db.add(new_rate)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            # Already exists (race condition), ignore.

    @classmethod
    async def _fetch_from_api(
        cls,
        base_currency: str,
        target_currency: str,
        target_date: date
    ) -> Optional[Decimal]:
        date_str = target_date.strftime("%Y-%m-%d")
        # If it's today's date, we could use /latest, but YYYY-MM-DD works too.
        url = f"{cls.BASE_URL}/{date_str}"
        params = {
            "from": base_currency,
            "to": target_currency
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                rates = data.get("rates", {})
                if target_currency in rates:
                    return Decimal(str(rates[target_currency]))
                
            # If the specific date is a weekend or holiday, Frankfurter might return the closest previous date.
            # However, if it returns 404, it might be a future date or totally unsupported currency.
            elif response.status_code == 404:
                logger.warning(f"Frankfurter API returned 404 for {base_currency} to {target_currency} on {date_str}. Trying /latest...")
                # Try latest as fallback
                url = f"{cls.BASE_URL}/latest"
                response = await client.get(url, params=params, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    rates = data.get("rates", {})
                    if target_currency in rates:
                        return Decimal(str(rates[target_currency]))
                        
            logger.warning(f"Frankfurter API error: {response.status_code} - {response.text}")
            return None
