"""
AI CFO — Dashboard Service
Aggregation logic for the main dashboard, with Redis caching.
"""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, func, extract, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Transaction, Budget, Alert, TransactionType
from schemas import DashboardSummary, CategoryAmount, TransactionOut
from cache import cache_get, cache_set, make_cache_key


async def get_dashboard_summary(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    months: int = 6,
) -> DashboardSummary:
    """Build the full dashboard summary with caching."""
    cache_key = make_cache_key("dashboard", str(workspace_id), str(months))
    cached = await cache_get(cache_key)
    if cached:
        return DashboardSummary(**cached)

    ws_id = workspace_id
    cutoff = datetime.utcnow() - timedelta(days=months * 30)

    # ── Total income & expenses ───────────────────────────────────
    totals = await db.execute(
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

    total_income = 0.0
    total_expenses = 0.0
    txn_count = 0
    for row in totals:
        if row[0] == TransactionType.income:
            total_income = float(row[1] or 0)
        else:
            total_expenses = float(row[1] or 0)
        txn_count += int(row[2] or 0)

    net_cash_flow = total_income - total_expenses
    burn_rate = total_expenses / max(months, 1)
    cash_balance = net_cash_flow  # Simplified: cumulative net
    runway = cash_balance / burn_rate if burn_rate > 0 else 99.0

    # ── Monthly breakdowns ────────────────────────────────────────
    monthly_q = await db.execute(
        select(
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
        .group_by("m", Transaction.type)
        .order_by("m")
    )

    monthly_income = [0.0] * 12
    monthly_expenses = [0.0] * 12
    for row in monthly_q:
        idx = int(row[0]) - 1
        if 0 <= idx < 12:
            if row[1] == TransactionType.income:
                monthly_income[idx] = float(row[2] or 0)
            else:
                monthly_expenses[idx] = float(row[2] or 0)

    # ── Top categories ────────────────────────────────────────────
    cats_q = await db.execute(
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
    top_categories = [
        CategoryAmount(category=r[0], amount=float(r[1]))
        for r in cats_q
    ]

    # ── Budget utilization ────────────────────────────────────────
    budget_q = await db.execute(
        select(
            func.sum(Budget.current_spend),
            func.sum(Budget.monthly_limit),
        )
        .where(Budget.workspace_id == ws_id)
    )
    budget_row = budget_q.one_or_none()
    spent = float(budget_row[0] or 0) if budget_row else 0.0
    limit_total = float(budget_row[1] or 1) if budget_row else 1.0
    budget_util = (spent / limit_total * 100) if limit_total > 0 else 0.0

    # ── Active alerts ─────────────────────────────────────────────
    alert_count_q = await db.execute(
        select(func.count(Alert.id))
        .where(
            and_(
                Alert.workspace_id == ws_id,
                Alert.is_read == False,
                Alert.is_dismissed == False,
            )
        )
    )
    active_alerts = alert_count_q.scalar() or 0

    # ── Recent transactions ───────────────────────────────────────
    recent_q = await db.execute(
        select(Transaction)
        .where(Transaction.workspace_id == ws_id)
        .order_by(Transaction.date.desc())
        .limit(10)
    )
    recent = [TransactionOut.model_validate(t) for t in recent_q.scalars()]

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
        monthly_income=monthly_income[:months],
        monthly_expenses=monthly_expenses[:months],
        top_categories=top_categories,
        recent_transactions=recent,
        period_months=months,
    )

    # Cache for 5 min
    await cache_set(cache_key, result.model_dump(), ttl=300)
    return result
