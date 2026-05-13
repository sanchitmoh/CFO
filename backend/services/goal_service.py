"""
Shared goal metric helpers.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Goal, Transaction, TransactionType


AUTO_TRACKED_METRIC_TYPES = {"revenue"}


@dataclass(frozen=True)
class GoalSnapshot:
    id: uuid.UUID
    title: str
    target_value: float
    current_value: float
    metric_type: str
    deadline: datetime | None
    status: str
    progress_pct: float
    created_at: datetime
    is_auto_tracked: bool


def normalize_goal_deadline(value: date | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def compute_goal_progress(metric_type: str, current_value: float, target_value: float) -> float:
    if target_value <= 0:
        return 100.0

    if metric_type == "expense_reduction":
        if current_value <= 0:
            return 100.0
        progress = target_value / current_value * 100
    else:
        progress = current_value / target_value * 100

    return round(max(0.0, min(progress, 100.0)), 1)


def is_goal_complete(metric_type: str, current_value: float, target_value: float) -> bool:
    if target_value <= 0:
        return True
    if metric_type == "expense_reduction":
        return current_value <= target_value
    return current_value >= target_value


def should_auto_track_goal(goal: Goal) -> bool:
    return (
        goal.metric_type in AUTO_TRACKED_METRIC_TYPES
        and float(goal.current_value or 0) == 0.0
    )


async def resolve_goal_current_value(
    db: AsyncSession,
    workspace_id,
    goal: Goal,
) -> tuple[float, bool]:
    if not should_auto_track_goal(goal):
        return float(goal.current_value or 0), False

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1)

    result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(
            and_(
                Transaction.workspace_id == workspace_id,
                Transaction.type == TransactionType.income,
                Transaction.date >= month_start,
                Transaction.date < month_end,
            )
        )
    )
    return float(result.scalar() or 0), True


async def build_goal_snapshot(
    db: AsyncSession,
    workspace_id,
    goal: Goal,
) -> GoalSnapshot:
    current_value, is_auto_tracked = await resolve_goal_current_value(
        db, workspace_id, goal
    )
    target_value = float(goal.target_value or 0)

    return GoalSnapshot(
        id=goal.id,
        title=goal.title,
        target_value=target_value,
        current_value=round(current_value, 2),
        metric_type=goal.metric_type,
        deadline=goal.deadline,
        status=goal.status.value,
        progress_pct=compute_goal_progress(goal.metric_type, current_value, target_value),
        created_at=goal.created_at,
        is_auto_tracked=is_auto_tracked,
    )
