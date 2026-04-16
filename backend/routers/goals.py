"""
AI CFO — Goals Router (Feature 5)
Financial goal tracking with CRUD and progress computation.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user
from models import User, Goal, GoalStatus
from schemas import GoalCreate, GoalUpdate, GoalOut
from services.audit_service import log_action
from cache import cache_delete

router = APIRouter()


def _compute_progress(goal: Goal) -> float:
    """Compute progress percentage."""
    if goal.target_value <= 0:
        return 100.0
    return round(min(float(goal.current_value) / float(goal.target_value) * 100, 100), 1)


def _goal_to_out(goal: Goal) -> GoalOut:
    return GoalOut(
        id=goal.id,
        title=goal.title,
        target_value=float(goal.target_value),
        current_value=float(goal.current_value),
        metric_type=goal.metric_type,
        deadline=goal.deadline,
        status=goal.status.value,
        progress_pct=_compute_progress(goal),
        created_at=goal.created_at,
    )


@router.get("/", response_model=list[GoalOut])
async def list_goals(
    status_filter: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all goals for the workspace."""
    query = select(Goal).where(Goal.workspace_id == user.workspace_id)
    if status_filter:
        query = query.where(Goal.status == status_filter)
    query = query.order_by(Goal.created_at.desc())

    result = await db.execute(query)
    return [_goal_to_out(g) for g in result.scalars()]


@router.post("/", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
async def create_goal(
    data: GoalCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new financial goal."""
    goal = Goal(
        workspace_id=user.workspace_id,
        user_id=user.id,
        title=data.title,
        target_value=data.target_value,
        metric_type=data.metric_type,
        deadline=data.deadline,
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)

    await log_action(db, user, "goal.create", "goal", goal.id,
                     new_value={"title": data.title, "target": data.target_value})

    return _goal_to_out(goal)


@router.put("/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: uuid.UUID,
    data: GoalUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a goal's progress or status."""
    result = await db.execute(
        select(Goal).where(
            and_(Goal.id == goal_id, Goal.workspace_id == user.workspace_id)
        )
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    old_value = {"current_value": float(goal.current_value), "status": goal.status.value}

    if data.title is not None:
        goal.title = data.title
    if data.target_value is not None:
        goal.target_value = data.target_value
    if data.current_value is not None:
        goal.current_value = data.current_value
    if data.status is not None:
        goal.status = GoalStatus(data.status)
    if data.deadline is not None:
        goal.deadline = data.deadline

    # Auto-complete if current >= target
    if float(goal.current_value) >= float(goal.target_value):
        goal.status = GoalStatus.completed

    await db.commit()
    await db.refresh(goal)

    await log_action(db, user, "goal.update", "goal", goal.id,
                     old_value=old_value,
                     new_value={"current_value": float(goal.current_value), "status": goal.status.value})

    return _goal_to_out(goal)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a goal."""
    result = await db.execute(
        select(Goal).where(
            and_(Goal.id == goal_id, Goal.workspace_id == user.workspace_id)
        )
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    await log_action(db, user, "goal.delete", "goal", goal.id,
                     old_value={"title": goal.title})
    await db.delete(goal)
    await db.commit()
