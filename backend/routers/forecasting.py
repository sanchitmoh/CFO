"""
AI CFO — Forecasting Router
Linear regression forecast with scenario modeling and caching.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, extract, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user
from models import User, Transaction, TransactionType, ForecastResult
from schemas import ForecastResponse, ForecastPoint
from cache import cache_get, cache_set, make_cache_key, compute_data_hash

router = APIRouter()


@router.get("/", response_model=ForecastResponse)
async def get_forecast(
    months_ahead: int = Query(6, ge=1, le=24),
    scenario: str = Query("base", regex="^(optimistic|base|pessimistic)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a cash flow forecast for the workspace."""
    ws_id = user.workspace_id
    cache_key = make_cache_key("forecast", str(ws_id), scenario, str(months_ahead))

    cached = await cache_get(cache_key)
    if cached:
        return ForecastResponse(**cached)

    # ── Get historical monthly data ──────────────────────────────
    cutoff = datetime.utcnow() - timedelta(days=365)

    monthly_q = await db.execute(
        select(
            extract("year", Transaction.date).label("y"),
            extract("month", Transaction.date).label("m"),
            Transaction.type,
            func.sum(Transaction.amount),
        )
        .where(and_(Transaction.workspace_id == ws_id, Transaction.date >= cutoff))
        .group_by("y", "m", Transaction.type)
        .order_by("y", "m")
    )

    monthly_data: dict[str, dict] = {}
    for row in monthly_q:
        key = f"{int(row[0])}-{int(row[1]):02d}"
        if key not in monthly_data:
            monthly_data[key] = {"income": 0.0, "expenses": 0.0}
        if row[2] == TransactionType.income:
            monthly_data[key]["income"] = float(row[3] or 0)
        else:
            monthly_data[key]["expenses"] = float(row[3] or 0)

    if not monthly_data:
        return ForecastResponse(
            scenario=scenario,
            months_ahead=months_ahead,
            historical_months=0,
            data_points=[],
            model_version="v1_linear",
        )

    # ── Simple linear trend ──────────────────────────────────────
    periods = sorted(monthly_data.keys())
    incomes = [monthly_data[p]["income"] for p in periods]
    expenses = [monthly_data[p]["expenses"] for p in periods]

    n = len(periods)
    avg_income = sum(incomes) / n
    avg_expense = sum(expenses) / n

    # Compute linear slope
    def _slope(values):
        n_ = len(values)
        if n_ < 2:
            return 0.0
        x_mean = (n_ - 1) / 2
        y_mean = sum(values) / n_
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        den = sum((i - x_mean) ** 2 for i in range(n_))
        return num / den if den != 0 else 0.0

    income_slope = _slope(incomes)
    expense_slope = _slope(expenses)

    # ── Scenario multipliers ─────────────────────────────────────
    multipliers = {
        "optimistic": {"income": 1.15, "expenses": 0.9},
        "base": {"income": 1.0, "expenses": 1.0},
        "pessimistic": {"income": 0.85, "expenses": 1.1},
    }
    mult = multipliers[scenario]

    # ── Generate forecast points ─────────────────────────────────
    now = datetime.utcnow()
    cumulative = 0.0
    data_points = []

    for i in range(months_ahead):
        future_month = now.month + i
        future_year = now.year + (future_month - 1) // 12
        future_month = ((future_month - 1) % 12) + 1
        period = f"{future_year}-{future_month:02d}"

        proj_income = max(0, (avg_income + income_slope * (n + i)) * mult["income"])
        proj_expense = max(0, (avg_expense + expense_slope * (n + i)) * mult["expenses"])
        proj_net = proj_income - proj_expense
        cumulative += proj_net

        # Confidence decays with distance
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

    result = ForecastResponse(
        scenario=scenario,
        months_ahead=months_ahead,
        historical_months=n,
        data_points=data_points,
        model_version="v1_linear",
    )

    # Cache for 30 min
    await cache_set(cache_key, result.model_dump(), ttl=1800)
    return result
