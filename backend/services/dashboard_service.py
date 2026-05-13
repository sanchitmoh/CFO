"""
AI CFO — Dashboard Service
Aggregation logic for the main dashboard, with Redis caching.

PERF-001: All 6 independent DB queries run in parallel via asyncio.gather
with separate sessions, reducing dashboard load from ~180ms to ~30ms on
cache miss (6×30ms serial → 1×30ms parallel).

SEC-002: Each parallel session sets the RLS workspace_id variable so that
Row-Level Security policies are enforced even in background queries.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, extract, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models import Transaction, Alert, TransactionType
from schemas import DashboardSummary, CategoryAmount, TransactionOut
from cache import cache_get, cache_set, make_versioned_cache_key
from services.budget_service import get_budget_totals

import logging
logger = logging.getLogger(__name__)


def _build_month_periods(cutoff: datetime, months: int) -> list[str]:
    """Return YYYY-MM labels aligned to the dashboard aggregation window."""
    periods: list[str] = []
    year = cutoff.year
    month = cutoff.month

    for offset in range(months + 1):
        total_month = month - 1 + offset
        period_year = year + total_month // 12
        period_month = total_month % 12 + 1
        periods.append(f"{period_year}-{period_month:02d}")

    return periods


async def _run_query(query_fn, workspace_id: uuid.UUID):
    """Execute a query in an independent session for parallel execution.

    Each session gets its own connection from the pool, allowing true
    concurrent I/O to the database via asyncio.gather.

    SEC-002: Sets the RLS workspace_id so row-level security policies
    are enforced in every parallel session.
    """
    async with AsyncSessionLocal() as session:
        if not session.in_transaction():
            await session.begin()
        ws_str = str(workspace_id)
        await session.execute(
            text(f"SET LOCAL app.workspace_id = '{ws_str}'")
        )
        return await query_fn(session)


async def get_dashboard_summary(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    months: int = 6,
) -> DashboardSummary:
    """Build the full dashboard summary with caching."""
    # PERF-002: Versioned cache key — auto-misses after invalidate_workspace_cache
    cache_key = await make_versioned_cache_key("dashboard", str(workspace_id), str(months))
    cached = await cache_get(cache_key)
    if cached:
        return DashboardSummary(**cached)

    ws_id = workspace_id

    # ── Compute the date window ───────────────────────────────────
    # Use the most recent transaction date as the anchor instead of
    # "now", so dashboards with historical data (e.g. a 2024 CSV
    # imported in 2026) render correctly.
    async def q_date_range(s: AsyncSession):
        return await s.execute(
            select(
                func.max(Transaction.date),
                func.min(Transaction.date),
            ).where(Transaction.workspace_id == ws_id)
        )

    date_range_result = await _run_query(q_date_range, ws_id)
    date_row = date_range_result.one_or_none()
    latest_date = date_row[0] if date_row and date_row[0] else datetime.now(timezone.utc)
    earliest_date = date_row[1] if date_row and date_row[1] else latest_date

    # Make latest_date timezone-aware if it isn't already
    if latest_date.tzinfo is None:
        latest_date = latest_date.replace(tzinfo=timezone.utc)
    if earliest_date.tzinfo is None:
        earliest_date = earliest_date.replace(tzinfo=timezone.utc)

    # Cutoff = N months before the latest transaction (not "now")
    cutoff = latest_date - timedelta(days=months * 30)
    # But never earlier than the earliest transaction
    if cutoff < earliest_date:
        cutoff = earliest_date

    logger.info(
        "Dashboard query: workspace=%s  latest=%s  earliest=%s  cutoff=%s  months=%d",
        ws_id, latest_date, earliest_date, cutoff, months,
    )

    # ── PERF-001: Build all 6 queries as coroutines ───────────────
    async def q_totals(s: AsyncSession):
        return await s.execute(
            select(
                Transaction.type,
                func.sum(Transaction.amount),
                func.count(Transaction.id),
            )
            .where(
                and_(
                    Transaction.workspace_id == ws_id,
                    Transaction.date >= cutoff,
                )
            )
            .group_by(Transaction.type)
        )

    async def q_monthly(s: AsyncSession):
        return await s.execute(
            select(
                extract("year", Transaction.date).label("y"),
                extract("month", Transaction.date).label("m"),
                Transaction.type,
                func.sum(Transaction.amount),
            )
            .where(
                and_(
                    Transaction.workspace_id == ws_id,
                    Transaction.date >= cutoff,
                )
            )
            .group_by("y", "m", Transaction.type)
            .order_by("y", "m")
        )

    async def q_categories(s: AsyncSession):
        return await s.execute(
            select(Transaction.category, func.sum(Transaction.amount))
            .where(
                and_(
                    Transaction.workspace_id == ws_id,
                    Transaction.type == TransactionType.expense,
                    Transaction.date >= cutoff,
                )
            )
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(5)
        )

    async def q_budget(s: AsyncSession):
        return await get_budget_totals(s, ws_id)

    async def q_alerts(s: AsyncSession):
        return await s.execute(
            select(func.count(Alert.id))
            .where(
                and_(
                    Alert.workspace_id == ws_id,
                    Alert.is_read.is_(False),
                    Alert.is_dismissed.is_(False),
                )
            )
        )

    async def q_recent(s: AsyncSession):
        return await s.execute(
            select(Transaction)
            .where(Transaction.workspace_id == ws_id)
            .order_by(Transaction.date.desc())
            .limit(10)
        )

    # ── Fire all 6 queries in parallel ────────────────────────────
    (
        totals_result,
        monthly_result,
        cats_result,
        budget_result,
        alert_result,
        recent_result,
    ) = await asyncio.gather(
        _run_query(q_totals, ws_id),
        _run_query(q_monthly, ws_id),
        _run_query(q_categories, ws_id),
        _run_query(q_budget, ws_id),
        _run_query(q_alerts, ws_id),
        _run_query(q_recent, ws_id),
    )

    # ── Process results ───────────────────────────────────────────
    total_income = 0.0
    total_expenses = 0.0
    txn_count = 0
    totals_rows = totals_result.fetchall()
    logger.info("Dashboard totals raw rows: %s", totals_rows)
    for row in totals_rows:
        if row[0] == TransactionType.income:
            total_income = float(row[1] or 0)
        else:
            total_expenses = float(row[1] or 0)
        txn_count += int(row[2] or 0)

    logger.info(
        "Dashboard result: income=%.2f  expenses=%.2f  count=%d",
        total_income, total_expenses, txn_count,
    )

    net_cash_flow = total_income - total_expenses
    burn_rate = total_expenses / max(months, 1)
    cash_balance = net_cash_flow  # Simplified: cumulative net
    runway = cash_balance / burn_rate if burn_rate > 0 else 99.0

    # Build monthly arrays relative to the cutoff date, not calendar month.
    # Each slot = one month, slot 0 = cutoff month, slot N-1 = latest month.
    cutoff_year = cutoff.year
    cutoff_month = cutoff.month
    monthly_income = [0.0] * (months + 1)
    monthly_expenses = [0.0] * (months + 1)
    monthly_periods = _build_month_periods(cutoff, months)
    for row in monthly_result:
        y, m = int(row[0]), int(row[1])
        # Relative offset: how many months after the cutoff month
        idx = (y - cutoff_year) * 12 + (m - cutoff_month)
        if 0 <= idx <= months:
            if row[2] == TransactionType.income:
                monthly_income[idx] = float(row[3] or 0)
            else:
                monthly_expenses[idx] = float(row[3] or 0)

    top_categories = [
        CategoryAmount(category=r[0], amount=float(r[1]))
        for r in cats_result
    ]

    spent, limit_total = budget_result
    budget_util = (spent / limit_total * 100) if limit_total > 0 else 0.0

    active_alerts = alert_result.scalar() or 0

    recent = [TransactionOut.model_validate(t) for t in recent_result.scalars()]

    result = DashboardSummary(
        total_income=total_income,
        total_expenses=total_expenses,
        net_cash_flow=net_cash_flow,
        transaction_count=txn_count,
        burn_rate=round(burn_rate, 2),
        runway_months=round(runway, 1),
        budget_utilization=round(budget_util, 1),
        active_alerts=active_alerts,
        cash_balance=round(cash_balance, 2),
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        monthly_periods=monthly_periods,
        top_categories=top_categories,
        recent_transactions=recent,
        period_months=months,
    )

    # Cache for 5 min
    await cache_set(cache_key, result.model_dump(), ttl=300)
    return result
