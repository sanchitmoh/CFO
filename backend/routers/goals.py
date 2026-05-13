"""
AI CFO — Goals Router (Feature 5)
Financial goal tracking with CRUD and progress computation.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_rls_db
from auth import get_current_user
from models import User, Goal, GoalStatus
from schemas import GoalCreate, GoalUpdate, GoalOut
from services.audit_service import log_action
from services.goal_service import (
    GoalSnapshot,
    build_goal_snapshot,
    is_goal_complete,
    normalize_goal_deadline,
)

router = APIRouter()


def _goal_to_out(goal: GoalSnapshot) -> GoalOut:
    return GoalOut(
        id=goal.id,
        title=goal.title,
        target_value=goal.target_value,
        current_value=goal.current_value,
        metric_type=goal.metric_type,
        deadline=goal.deadline,
        status=goal.status,
        progress_pct=goal.progress_pct,
        created_at=goal.created_at,
        is_auto_tracked=goal.is_auto_tracked,
    )


@router.get("/", response_model=list[GoalOut])
async def list_goals(
    status_filter: GoalStatus | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """List all goals for the workspace.

    MED-006: status_filter is validated against GoalStatus enum.
    Valid values: active, completed, abandoned.
    """
    query = select(Goal).where(Goal.workspace_id == user.workspace_id)
    if status_filter is not None:
        query = query.where(Goal.status == status_filter)
    query = query.order_by(Goal.created_at.desc())

    result = await db.execute(query)
    snapshots = [
        await build_goal_snapshot(db, user.workspace_id, goal)
        for goal in result.scalars()
    ]
    return [_goal_to_out(snapshot) for snapshot in snapshots]


@router.post("/", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
async def create_goal(
    data: GoalCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Create a new financial goal."""
    goal = Goal(
        workspace_id=user.workspace_id,
        user_id=user.id,
        title=data.title,
        target_value=data.target_value,
        current_value=data.current_value or 0,
        metric_type=data.metric_type,
        deadline=normalize_goal_deadline(data.deadline),
    )
    if is_goal_complete(goal.metric_type, float(goal.current_value or 0), float(goal.target_value)):
        goal.status = GoalStatus.completed

    db.add(goal)
    await db.commit()
    await db.refresh(goal)

    await log_action(db, user, "goal.create", "goal", goal.id,
                     new_value={"title": data.title, "target": data.target_value})

    snapshot = await build_goal_snapshot(db, user.workspace_id, goal)
    return _goal_to_out(snapshot)


@router.put("/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: uuid.UUID,
    data: GoalUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
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
        goal.deadline = normalize_goal_deadline(data.deadline)

    if (
        goal.status != GoalStatus.abandoned
        and is_goal_complete(
            goal.metric_type,
            float(goal.current_value or 0),
            float(goal.target_value or 0),
        )
    ):
        goal.status = GoalStatus.completed

    await db.commit()
    await db.refresh(goal)

    await log_action(db, user, "goal.update", "goal", goal.id,
                     old_value=old_value,
                     new_value={"current_value": float(goal.current_value), "status": goal.status.value})

    snapshot = await build_goal_snapshot(db, user.workspace_id, goal)
    return _goal_to_out(snapshot)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
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
