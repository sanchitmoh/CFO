"""
AI CFO — Prophet Forecast Service (EXT-001 Alternative)
Time-series forecasting using Facebook Prophet with seasonality detection.

This is a drop-in replacement for LinearForecastService that uses Prophet's
advanced time-series modeling instead of simple linear regression.

To activate: Update get_forecast_service() in dependencies.py to return
ProphetForecastService() instead of LinearForecastService().
"""
import json
import hashlib
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import select, func, extract, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Transaction, TransactionType, ForecastResult, Workspace
from schemas import ForecastResponse, ForecastPoint
from cache import cache_get, cache_set, make_versioned_cache_key

logger = logging.getLogger(__name__)
PROPHET_MODEL_VERSION = "v2_prophet"

# Prophet is an optional dependency — gracefully degrade if not installed
try:
    from prophet import Prophet
    import pandas as pd
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.warning(
        "Prophet not installed. Install with: pip install prophet"
    )


SCENARIO_MULTIPLIERS = {
    "optimistic": {"income": 1.15, "expenses": 0.9},
    "base":       {"income": 1.0,  "expenses": 1.0},
    "pessimistic":{"income": 0.85, "expenses": 1.1},
}


async def _resolve_base_currency(db: AsyncSession, workspace_id: uuid.UUID) -> str:
    workspace = await db.get(Workspace, workspace_id)
    currency = getattr(workspace, "currency", None)
    if isinstance(currency, str) and currency.strip():
        return currency.upper()
    return "USD"


def _with_base_currency(payload: dict, base_currency: str) -> dict:
    result = dict(payload)
    result["base_currency"] = base_currency
    return result


async def _fetch_monthly_data(
    db: AsyncSession, workspace_id
) -> tuple[dict[str, dict], str]:
    """Fetch historical monthly aggregates and compute a data hash."""
    date_range = await db.execute(
        select(func.max(Transaction.date))
        .where(Transaction.workspace_id == workspace_id)
    )
    latest_date = date_range.scalar()
    if latest_date is None:
        return {}, hashlib.sha256(b"[]").hexdigest()

    if latest_date.tzinfo is None:
        latest_date = latest_date.replace(tzinfo=timezone.utc)

    cutoff = latest_date - timedelta(days=365)

    monthly_q = await db.execute(
        select(
            extract("year", Transaction.date).label("y"),
            extract("month", Transaction.date).label("m"),
            Transaction.type,
            func.sum(Transaction.amount),
        )
        .where(and_(Transaction.workspace_id == workspace_id, Transaction.date >= cutoff))
        .group_by("y", "m", Transaction.type)
        .order_by("y", "m")
    )

    monthly_data: dict[str, dict] = {}
    raw_for_hash: list[dict] = []
    for row in monthly_q:
        key = f"{int(row[0])}-{int(row[1]):02d}"
        if key not in monthly_data:
            monthly_data[key] = {"income": 0.0, "expenses": 0.0}
        amount = float(row[3] or 0)
        if row[2] == TransactionType.income:
            monthly_data[key]["income"] = amount
        else:
            monthly_data[key]["expenses"] = amount
        raw_for_hash.append({"key": key, "type": str(row[2]), "amount": amount})

    data_hash = hashlib.sha256(
        json.dumps(raw_for_hash, sort_keys=True).encode()
    ).hexdigest()

    return monthly_data, data_hash


def _compute_forecast_prophet(
    monthly_data: dict[str, dict],
    months_ahead: int,
    scenario: str,
) -> list[ForecastPoint]:
    """
    Prophet-based forecast with automatic seasonality detection.
    
    Prophet advantages over linear regression:
    - Detects weekly/monthly/yearly seasonality
    - Handles missing data and outliers
    - Provides uncertainty intervals
    - Captures trend changes (growth/decline)
    """
    if not PROPHET_AVAILABLE:
        logger.error("Prophet not available — cannot compute forecast")
        return []
    
    if not monthly_data or len(monthly_data) < 3:
        logger.warning("Insufficient data for Prophet (need 3+ months)")
        return []

    periods = sorted(monthly_data.keys())
    
    # ── Prepare income dataframe ──────────────────────────────────
    income_df = pd.DataFrame([
        {
            "ds": pd.to_datetime(f"{period}-01"),
            "y": monthly_data[period]["income"]
        }
        for period in periods
    ])
    
    # ── Prepare expense dataframe ─────────────────────────────────
    expense_df = pd.DataFrame([
        {
            "ds": pd.to_datetime(f"{period}-01"),
            "y": monthly_data[period]["expenses"]
        }
        for period in periods
    ])
    
    # ── Train Prophet models ──────────────────────────────────────
    # Suppress Prophet's verbose logging
    import logging as prophet_logging
    prophet_logging.getLogger('prophet').setLevel(prophet_logging.WARNING)
    
    income_model = Prophet(
        yearly_seasonality=True if len(periods) >= 12 else False,
        weekly_seasonality=False,  # Monthly data doesn't need weekly
        daily_seasonality=False,
        interval_width=0.8,  # 80% confidence interval
        changepoint_prior_scale=0.05,  # Flexibility in trend changes
    )
    income_model.fit(income_df)
    
    expense_model = Prophet(
        yearly_seasonality=True if len(periods) >= 12 else False,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.8,
        changepoint_prior_scale=0.05,
    )
    expense_model.fit(expense_df)
    
    # ── Generate future dates ─────────────────────────────────────
    future_dates = income_model.make_future_dataframe(
        periods=months_ahead,
        freq='MS'  # Month start
    )
    
    # ── Predict ───────────────────────────────────────────────────
    income_forecast = income_model.predict(future_dates)
    expense_forecast = expense_model.predict(future_dates)
    
    # ── Extract future predictions only ───────────────────────────
    income_future = income_forecast.tail(months_ahead)
    expense_future = expense_forecast.tail(months_ahead)
    
    # ── Apply scenario multipliers ────────────────────────────────
    mult = SCENARIO_MULTIPLIERS[scenario]
    
    data_points = []
    cumulative = 0.0
    
    for i in range(months_ahead):
        date = income_future.iloc[i]['ds']
        period = date.strftime('%Y-%m')
        
        # Prophet predictions with scenario adjustment
        proj_income = max(0, income_future.iloc[i]['yhat'] * mult["income"])
        proj_expense = max(0, expense_future.iloc[i]['yhat'] * mult["expenses"])
        proj_net = proj_income - proj_expense
        cumulative += proj_net
        
        # Prophet provides uncertainty intervals
        income_lower = max(0, income_future.iloc[i]['yhat_lower'] * mult["income"])
        income_upper = max(0, income_future.iloc[i]['yhat_upper'] * mult["income"])
        expense_lower = max(0, expense_future.iloc[i]['yhat_lower'] * mult["expenses"])
        expense_upper = max(0, expense_future.iloc[i]['yhat_upper'] * mult["expenses"])
        
        net_lower = income_lower - expense_upper
        net_upper = income_upper - expense_lower
        interval_width = max(net_upper - net_lower, 0.0)
        activity = max(abs(proj_income) + abs(proj_expense), 1.0)
        confidence = max(0.5, min(0.95, 1.0 - (interval_width / activity)))
        
        data_points.append(ForecastPoint(
            period=period,
            projected_income=round(proj_income, 2),
            projected_expenses=round(proj_expense, 2),
            projected_net=round(proj_net, 2),
            cumulative_net=round(cumulative, 2),
            confidence=round(confidence, 2),
            confidence_lower=round(net_lower, 2),
            confidence_upper=round(net_upper, 2),
        ))
    
    return data_points


class ProphetForecastService:
    """
    EXT-001: Protocol-compatible forecast implementation using Facebook Prophet.
    
    Advantages over LinearForecastService:
    - Automatic seasonality detection (yearly patterns)
    - Better handling of trend changes
    - Uncertainty quantification via confidence intervals
    - Robust to missing data and outliers
    
    Satisfies ``ForecastService`` Protocol defined in ``forecast_protocol.py``.
    Register via ``get_forecast_service()`` in ``dependencies.py``.
    """

    async def generate_forecast(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        months_ahead: int = 6,
        scenario: Literal["optimistic", "base", "pessimistic"] = "base",
    ) -> ForecastResponse:
        """
        Generate a cash-flow forecast using Prophet time-series modeling.
        
        Uses the same read-through cache pattern as LinearForecastService:
          Redis hit → return
          Redis miss → check DB (validate data_hash) → return if fresh
          DB miss / stale → recompute → persist to DB → cache in Redis
        """
        if not PROPHET_AVAILABLE:
            logger.error("Prophet not installed — cannot generate forecast")
            base_currency = await _resolve_base_currency(db, workspace_id)
            return ForecastResponse(
                scenario=scenario,
                base_currency=base_currency,
                months_ahead=months_ahead,
                historical_months=0,
                data_points=[],
                model_version="prophet_unavailable",
            )
        
        base_currency = await _resolve_base_currency(db, workspace_id)
        cache_key = await make_versioned_cache_key(
            "forecast_prophet_v2", str(workspace_id), scenario, str(months_ahead)
        )

        # ── Layer 1: Redis hot cache ─────────────────────────────────
        cached = await cache_get(cache_key)
        if cached:
            logger.info("Prophet forecast cache HIT for workspace %s", workspace_id)
            cached_result = _with_base_currency(cached, base_currency)
            if cached_result != cached:
                await cache_set(cache_key, cached_result, ttl=1800)
            return ForecastResponse(**cached_result)

        # ── Fetch current source data + hash ─────────────────────────
        monthly_data, current_hash = await _fetch_monthly_data(db, workspace_id)

        # ── Layer 2: PostgreSQL persistent store ─────────────────────
        db_result = await db.execute(
            select(ForecastResult)
            .where(and_(
                ForecastResult.workspace_id == workspace_id,
                ForecastResult.scenario == scenario,
                ForecastResult.horizon_months == months_ahead,
                ForecastResult.model_version == PROPHET_MODEL_VERSION,
            ))
            .order_by(ForecastResult.computed_at.desc())
            .limit(1)
        )
        db_forecast = db_result.scalar_one_or_none()

        if (
            db_forecast
            and db_forecast.data_hash == current_hash
            and db_forecast.expires_at > datetime.now(timezone.utc)
        ):
            # DB record is fresh and data hasn't changed — use it
            logger.info("Prophet forecast DB HIT for workspace %s", workspace_id)
            response_dict = _with_base_currency(db_forecast.result_json, base_currency)
            if db_forecast.base_currency != base_currency or response_dict != db_forecast.result_json:
                db_forecast.base_currency = base_currency
                db_forecast.result_json = response_dict
                await db.commit()
            response = ForecastResponse(**response_dict)
            # Backfill Redis
            await cache_set(cache_key, response_dict, ttl=1800)
            return response

        # ── Layer 3: Recompute with Prophet ──────────────────────────
        logger.info("Computing Prophet forecast for workspace %s", workspace_id)
        
        if not monthly_data or len(monthly_data) < 3:
            return ForecastResponse(
                scenario=scenario,
                base_currency=base_currency,
                months_ahead=months_ahead,
                historical_months=0,
                data_points=[],
                model_version=PROPHET_MODEL_VERSION,
            )

        data_points = _compute_forecast_prophet(monthly_data, months_ahead, scenario)

        result = ForecastResponse(
            scenario=scenario,
            base_currency=base_currency,
            months_ahead=months_ahead,
            historical_months=len(monthly_data),
            data_points=data_points,
            model_version=PROPHET_MODEL_VERSION,
        )
        result_dict = result.model_dump()

        # ── Persist to DB (upsert) ───────────────────────────────────
        now = datetime.now(timezone.utc)
        if db_forecast:
            db_forecast.base_currency = base_currency
            db_forecast.result_json = result_dict
            db_forecast.data_hash = current_hash
            db_forecast.model_version = PROPHET_MODEL_VERSION
            db_forecast.computed_at = now
            db_forecast.expires_at = now + timedelta(minutes=30)
        else:
            db.add(ForecastResult(
                workspace_id=workspace_id,
                scenario=scenario,
                base_currency=base_currency,
                horizon_months=months_ahead,
                result_json=result_dict,
                model_version=PROPHET_MODEL_VERSION,
                data_hash=current_hash,
                computed_at=now,
                expires_at=now + timedelta(minutes=30),
            ))
        await db.commit()

        # ── Backfill Redis ───────────────────────────────────────────
        await cache_set(cache_key, result_dict, ttl=1800)

        logger.info(
            "Prophet forecast computed for workspace %s: %d data points",
            workspace_id, len(data_points)
        )
        return result


# ── Backwards-compatible module-level function ────────────────────────
# Kept so that any non-router code importing the bare function still works.
_default_service = ProphetForecastService()


async def generate_forecast_prophet(
    db: AsyncSession,
    workspace_id,
    months_ahead: int = 6,
    scenario: str = "base",
) -> ForecastResponse:
    """Module-level convenience wrapper for backwards compatibility."""
    return await _default_service.generate_forecast(
        db, workspace_id, months_ahead, scenario
    )
