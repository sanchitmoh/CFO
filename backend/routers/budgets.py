"""
AI CFO — Budgets Router
CRUD for category budgets with spend tracking.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_rls_db
from auth import get_current_user
from models import User, Budget
from schemas import BudgetCreate, BudgetOut
from services.audit_service import log_action
from cache import invalidate_workspace_cache
from services.budget_service import (
    BudgetSnapshot,
    current_budget_month,
    get_budget_snapshots,
    normalize_category_key,
    normalize_category_label,
    normalized_category_expr,
)

router = APIRouter()


async def _get_snapshot_for_budget(
    db: AsyncSession,
    workspace_id,
    budget: Budget,
) -> BudgetSnapshot:
    for snapshot in await get_budget_snapshots(db, workspace_id, month=budget.month):
        if snapshot.id == budget.id:
            return snapshot
    raise HTTPException(status_code=404, detail="Budget not found after update")


def _snapshot_to_out(snapshot: BudgetSnapshot) -> BudgetOut:
    return BudgetOut(
        id=snapshot.id,
        category=snapshot.category,
        monthly_limit=snapshot.monthly_limit,
        alert_threshold=snapshot.alert_threshold,
        current_spend=snapshot.current_spend,
        percentage_used=snapshot.percentage_used,
        status=snapshot.status,
        month=snapshot.month,
    )


@router.get("/", response_model=list[BudgetOut])
async def list_budgets(
    month: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """List all budgets for the workspace, optionally filtered by month."""
    snapshots = await get_budget_snapshots(db, user.workspace_id, month=month)
    return [_snapshot_to_out(snapshot) for snapshot in snapshots]


@router.post("/", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
async def create_budget(
    data: BudgetCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Create a new budget category for a month."""
    month = data.month or current_budget_month()
    category = normalize_category_label(data.category)

    # Check for duplicate
    existing = await db.execute(
        select(Budget).where(
            and_(
                Budget.workspace_id == user.workspace_id,
                normalized_category_expr(Budget.category) == normalize_category_key(category),
                Budget.month == month,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Budget for '{data.category}' in {month} already exists",
        )

    budget = Budget(
        workspace_id=user.workspace_id,
        user_id=user.id,
        category=category,
        monthly_limit=data.monthly_limit,
        alert_threshold=data.alert_threshold,
        month=month,
    )
    db.add(budget)
    await db.commit()
    await db.refresh(budget)

    await invalidate_workspace_cache(str(user.workspace_id))
    await log_action(db, user, "budget.create", "budget", budget.id,
                     new_value={"category": category, "limit": data.monthly_limit})

    return _snapshot_to_out(await _get_snapshot_for_budget(db, user.workspace_id, budget))


@router.put("/{budget_id}", response_model=BudgetOut)
async def update_budget(
    budget_id: uuid.UUID,
    data: BudgetCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Update a budget limit or threshold."""
    result = await db.execute(
        select(Budget).where(
            and_(Budget.id == budget_id, Budget.workspace_id == user.workspace_id)
        )
    )
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    old_limit = float(budget.monthly_limit)
    budget.monthly_limit = data.monthly_limit
    budget.alert_threshold = data.alert_threshold

    await db.commit()
    await db.refresh(budget)

    await invalidate_workspace_cache(str(user.workspace_id))
    await log_action(db, user, "budget.update", "budget", budget.id,
                     old_value={"limit": old_limit},
                     new_value={"limit": data.monthly_limit})

    return _snapshot_to_out(await _get_snapshot_for_budget(db, user.workspace_id, budget))


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Delete a budget."""
    result = await db.execute(
        select(Budget).where(
            and_(Budget.id == budget_id, Budget.workspace_id == user.workspace_id)
        )
    )
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    await log_action(db, user, "budget.delete", "budget", budget.id)
    await db.delete(budget)
    await db.commit()
    await invalidate_workspace_cache(str(user.workspace_id))
