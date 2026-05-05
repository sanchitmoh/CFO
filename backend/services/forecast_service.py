"""
AI CFO — Forecast Service (EXT-001 refactor)
Linear regression forecast with scenario modeling, wrapped in a Protocol-compatible class.

Storage hierarchy (ARCH-003):
  1. Redis (hot cache, 30-min TTL)
  2. PostgreSQL forecast_results (persistent, data_hash validated)
  3. Recompute from transactions → write DB → write Redis
"""
import json
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import select, func, extract, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Transaction, TransactionType, ForecastResult
from schemas import ForecastResponse, ForecastPoint
from cache import cache_get, cache_set, make_versioned_cache_key


def _slope(values: list[float]) -> float:
    """Compute a simple linear slope for a list of values by index."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den != 0 else 0.0


SCENARIO_MULTIPLIERS = {
    "optimistic": {"income": 1.15, "expenses": 0.9},
    "base":       {"income": 1.0,  "expenses": 1.0},
    "pessimistic":{"income": 0.85, "expenses": 1.1},
}


async def _fetch_monthly_data(
    db: AsyncSession, workspace_id
) -> tuple[dict[str, dict], str]:
    """Fetch historical monthly aggregates and compute a data hash."""
    # Anchor the lookback to the LATEST transaction, not "now",
    # so historical CSVs (e.g. 2024 data imported in 2026) are visible.
    date_range = await db.execute(
        select(func.max(Transaction.date))
        .where(Transaction.workspace_id == workspace_id)
    )
    latest_date = date_range.scalar()
    if latest_date is None:
        return {}, hashlib.sha256(b"[]").hexdigest()

    if latest_date.tzinfo is None:
        from datetime import timezone as tz
        latest_date = latest_date.replace(tzinfo=tz.utc)

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


def _compute_forecast(
    monthly_data: dict[str, dict],
    months_ahead: int,
    scenario: str,
) -> list[ForecastPoint]:
    """Pure computation — generates forecast points from historical data."""
    if not monthly_data:
        return []

    periods = sorted(monthly_data.keys())
    incomes = [monthly_data[p]["income"] for p in periods]
    expenses = [monthly_data[p]["expenses"] for p in periods]
    n = len(periods)

    avg_income = sum(incomes) / n
    avg_expense = sum(expenses) / n
    income_slope = _slope(incomes)
    expense_slope = _slope(expenses)

    mult = SCENARIO_MULTIPLIERS[scenario]
    # Start forecasting from the month AFTER the latest historical period,
    # not from "now", so historical CSV data projects forward correctly.
    last_period = periods[-1]  # e.g. "2024-11"
    last_year, last_month = int(last_period[:4]), int(last_period[5:])
    cumulative = 0.0
    data_points = []

    for i in range(months_ahead):
        future_month = last_month + 1 + i
        future_year = last_year + (future_month - 1) // 12
        future_month = ((future_month - 1) % 12) + 1
        period = f"{future_year}-{future_month:02d}"

        proj_income = max(0, (avg_income + income_slope * (n + i)) * mult["income"])
        proj_expense = max(0, (avg_expense + expense_slope * (n + i)) * mult["expenses"])
        proj_net = proj_income - proj_expense
        cumulative += proj_net

        confidence = max(0.5, 1.0 - i * 0.05)
        margin = proj_income * (1 - confidence) * 0.5

        data_points.append(ForecastPoint(
            period=period,
            projected_income=round(proj_income, 2),
            projected_expenses=round(proj_expense, 2),
            projected_net=round(proj_net, 2),
            cumulative_net=round(cumulative, 2),
            confidence=round(confidence, 2),
            confidence_lower=round(proj_net - margin, 2),
            confidence_upper=round(proj_net + margin, 2),
        ))

    return data_points


class LinearForecastService:
    """EXT-001: Protocol-compatible forecast implementation using linear regression.

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
        Generate a cash-flow forecast using the read-through cache pattern:
          Redis hit → return
          Redis miss → check DB (validate data_hash) → return if fresh
          DB miss / stale → recompute → persist to DB → cache in Redis
        """
        cache_key = await make_versioned_cache_key("forecast", str(workspace_id), scenario, str(months_ahead))

        # ── Layer 1: Redis hot cache ─────────────────────────────────
        cached = await cache_get(cache_key)
        if cached:
            return ForecastResponse(**cached)

        # ── Fetch current source data + hash ─────────────────────────
        monthly_data, current_hash = await _fetch_monthly_data(db, workspace_id)

        # ── Layer 2: PostgreSQL persistent store ─────────────────────
        db_result = await db.execute(
            select(ForecastResult)
            .where(and_(
                ForecastResult.workspace_id == workspace_id,
                ForecastResult.scenario == scenario,
                ForecastResult.horizon_months == months_ahead,
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
            response = ForecastResponse(**db_forecast.result_json)
            # Backfill Redis
            await cache_set(cache_key, db_forecast.result_json, ttl=1800)
            return response

        # ── Layer 3: Recompute ───────────────────────────────────────
        if not monthly_data:
            return ForecastResponse(
                scenario=scenario,
                months_ahead=months_ahead,
                historical_months=0,
                data_points=[],
                model_version="v1_linear",
            )

        data_points = _compute_forecast(monthly_data, months_ahead, scenario)

        result = ForecastResponse(
            scenario=scenario,
            months_ahead=months_ahead,
            historical_months=len(monthly_data),
            data_points=data_points,
            model_version="v1_linear",
        )
        result_dict = result.model_dump()

        # ── Persist to DB (upsert) ───────────────────────────────────
        now = datetime.now(timezone.utc)
        if db_forecast:
            db_forecast.result_json = result_dict
            db_forecast.data_hash = current_hash
            db_forecast.computed_at = now
            db_forecast.expires_at = now + timedelta(minutes=30)
        else:
            db.add(ForecastResult(
                workspace_id=workspace_id,
                scenario=scenario,
                horizon_months=months_ahead,
                result_json=result_dict,
                model_version="v1_linear",
                data_hash=current_hash,
                computed_at=now,
                expires_at=now + timedelta(minutes=30),
            ))
        await db.commit()

        # ── Backfill Redis ───────────────────────────────────────────
        await cache_set(cache_key, result_dict, ttl=1800)

        return result


# ── Backwards-compatible module-level function ────────────────────────
# Kept so that any non-router code importing the bare function still works.
_default_service = LinearForecastService()


async def generate_forecast(
    db: AsyncSession,
    workspace_id,
    months_ahead: int = 6,
    scenario: str = "base",
) -> ForecastResponse:
    """Module-level convenience wrapper for backwards compatibility."""
    return await _default_service.generate_forecast(
        db, workspace_id, months_ahead, scenario
    )
