"""
Shared budget calculation helpers.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Budget, Transaction, TransactionType


@dataclass(frozen=True)
class BudgetSnapshot:
    id: uuid.UUID
    category: str
    monthly_limit: float
    alert_threshold: float
    current_spend: float
    percentage_used: float
    status: str
    month: str


def current_budget_month(now: datetime | None = None) -> str:
    reference = now or datetime.now(timezone.utc)
    return reference.astimezone(timezone.utc).strftime("%Y-%m")


def normalize_category_label(value: str) -> str:
    return " ".join(value.strip().split())


def normalize_category_key(value: str) -> str:
    return normalize_category_label(value).casefold()


def normalized_category_expr(column):
    return func.lower(func.regexp_replace(func.trim(column), r"\s+", " ", "g"))


def get_month_bounds(month: str) -> tuple[datetime, datetime]:
    month_start = datetime.strptime(month, "%Y-%m").replace(tzinfo=timezone.utc)
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1)
    return month_start, month_end


def compute_budget_percentage(current_spend: float, monthly_limit: float) -> float:
    if monthly_limit <= 0:
        return 0.0
    return round(current_spend / monthly_limit * 100, 1)


def compute_budget_status(
    current_spend: float,
    monthly_limit: float,
    alert_threshold: float,
) -> str:
    percentage_used = compute_budget_percentage(current_spend, monthly_limit)
    threshold_pct = round(alert_threshold * 100, 1)

    if percentage_used >= 100:
        return "over_budget"
    if percentage_used >= threshold_pct:
        return "warning"
    return "on_track"


def build_budget_snapshot(budget: Budget, current_spend: float) -> BudgetSnapshot:
    monthly_limit = float(budget.monthly_limit or 0)
    normalized_category = normalize_category_label(budget.category)
    alert_threshold = float(budget.alert_threshold or 0)
    percentage_used = compute_budget_percentage(current_spend, monthly_limit)
    status = compute_budget_status(current_spend, monthly_limit, alert_threshold)

    return BudgetSnapshot(
        id=budget.id,
        category=normalized_category,
        monthly_limit=monthly_limit,
        alert_threshold=alert_threshold,
        current_spend=round(float(current_spend or 0), 2),
        percentage_used=percentage_used,
        status=status,
        month=budget.month,
    )


async def get_budget_snapshots(
    db: AsyncSession,
    workspace_id,
    month: str | None = None,
) -> list[BudgetSnapshot]:
    target_month = month or current_budget_month()
    month_start, month_end = get_month_bounds(target_month)

    txn_totals = (
        select(
            normalized_category_expr(Transaction.category).label("category_key"),
            func.coalesce(func.sum(Transaction.amount), 0).label("current_spend"),
        )
        .where(
            and_(
                Transaction.workspace_id == workspace_id,
                Transaction.type == TransactionType.expense,
                Transaction.date >= month_start,
                Transaction.date < month_end,
            )
        )
        .group_by("category_key")
        .subquery()
    )

    result = await db.execute(
        select(
            Budget,
            func.coalesce(txn_totals.c.current_spend, 0).label("current_spend"),
        )
        .outerjoin(
            txn_totals,
            normalized_category_expr(Budget.category) == txn_totals.c.category_key,
        )
        .where(
            and_(
                Budget.workspace_id == workspace_id,
                Budget.month == target_month,
            )
        )
        .order_by(Budget.category)
    )

    return [
        build_budget_snapshot(budget, float(current_spend or 0))
        for budget, current_spend in result.all()
    ]


async def get_budget_totals(
    db: AsyncSession,
    workspace_id,
    month: str | None = None,
) -> tuple[float, float]:
    snapshots = await get_budget_snapshots(db, workspace_id, month=month)
    total_spend = round(sum(snapshot.current_spend for snapshot in snapshots), 2)
    total_limit = round(sum(snapshot.monthly_limit for snapshot in snapshots), 2)
    return total_spend, total_limit
