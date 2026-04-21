"""
AI CFO — Budgets Router
CRUD for category budgets with spend tracking.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, get_db_with_rls
from auth import get_current_user
from models import User, Budget, Transaction, TransactionType
from schemas import BudgetCreate, BudgetOut
from services.audit_service import log_action
from cache import cache_delete

router = APIRouter()


def _budget_to_out(budget: Budget) -> BudgetOut:
    spent = float(budget.current_spend or 0)
    limit_val = float(budget.monthly_limit or 1)
    pct = round(spent / limit_val * 100, 1) if limit_val > 0 else 0

    if pct >= 100:
        status_ = "over_budget"
    elif pct >= budget.alert_threshold * 100:
        status_ = "warning"
    else:
        status_ = "on_track"

    return BudgetOut(
        id=budget.id,
        category=budget.category,
        monthly_limit=limit_val,
        alert_threshold=budget.alert_threshold,
        current_spend=spent,
        percentage_used=pct,
        status=status_,
        month=budget.month,
    )


@router.get("/", response_model=list[BudgetOut])
async def list_budgets(
    month: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all budgets for the workspace, optionally filtered by month."""
    current_month = month or datetime.utcnow().strftime("%Y-%m")

    query = select(Budget).where(
        and_(
            Budget.workspace_id == user.workspace_id,
            Budget.month == current_month,
        )
    ).order_by(Budget.category)

    result = await db.execute(query)
    budgets = list(result.scalars())

    # ── Recalculate current_spend from actual transactions ────────
    for budget in budgets:
        month_start = datetime.strptime(budget.month, "%Y-%m")
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)

        spend_q = await db.execute(
            select(func.sum(Transaction.amount))
            .where(
                and_(
                    Transaction.workspace_id == user.workspace_id,
                    Transaction.category == budget.category,
                    Transaction.type == TransactionType.expense,
                    Transaction.date >= month_start,
                    Transaction.date < month_end,
                )
            )
        )
        actual_spend = float(spend_q.scalar() or 0)
        budget.current_spend = actual_spend

    await db.commit()
    return [_budget_to_out(b) for b in budgets]


@router.post("/", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
async def create_budget(
    data: BudgetCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new budget category for a month."""
    month = data.month or datetime.utcnow().strftime("%Y-%m")

    # Check for duplicate
    existing = await db.execute(
        select(Budget).where(
            and_(
                Budget.workspace_id == user.workspace_id,
                Budget.category == data.category,
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
        category=data.category,
        monthly_limit=data.monthly_limit,
        alert_threshold=data.alert_threshold,
        month=month,
    )
    db.add(budget)
    await db.commit()
    await db.refresh(budget)

    await cache_delete(f"ws:{user.workspace_id}:dashboard:*")
    await log_action(db, user, "budget.create", "budget", budget.id,
                     new_value={"category": data.category, "limit": data.monthly_limit})

    return _budget_to_out(budget)


@router.put("/{budget_id}", response_model=BudgetOut)
async def update_budget(
    budget_id: uuid.UUID,
    data: BudgetCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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

    await cache_delete(f"ws:{user.workspace_id}:dashboard:*")
    await log_action(db, user, "budget.update", "budget", budget.id,
                     old_value={"limit": old_limit},
                     new_value={"limit": data.monthly_limit})

    return _budget_to_out(budget)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
    await cache_delete(f"ws:{user.workspace_id}:dashboard:*")
