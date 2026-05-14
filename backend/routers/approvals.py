"""
AI CFO — Expense Approval Router
Policy CRUD, submit for approval, approve/reject decisions.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_rls_db
from auth import get_current_user
from models import User
from schemas import (
    ApprovalPolicyCreate, ApprovalPolicyOut,
    ApprovalDecisionRequest, ExpenseApprovalOut,
)
from services import approval_service
from services.audit_service import log_action

router = APIRouter()


# ── Policies ───────────────────────────────────────────────────────

@router.get("/policies", response_model=list[ApprovalPolicyOut])
async def list_policies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    policies = await approval_service.list_policies(db, user.workspace_id)
    return [ApprovalPolicyOut.model_validate(p) for p in policies]


@router.post("/policies", response_model=ApprovalPolicyOut, status_code=status.HTTP_201_CREATED)
async def create_policy(
    data: ApprovalPolicyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    policy = await approval_service.create_policy(db, user.workspace_id, data)
    await db.commit()
    await log_action(db, user, "approval.policy.create", "approval_policy", policy.id,
                     new_value={"name": data.name})
    return ApprovalPolicyOut.model_validate(policy)


# ── Approvals ──────────────────────────────────────────────────────

@router.get("/", response_model=list[ExpenseApprovalOut])
async def list_approvals(
    status_filter: str | None = Query(None, alias="status"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    approvals = await approval_service.list_all_approvals(db, user.workspace_id, status_filter)
    return [ExpenseApprovalOut.model_validate(a) for a in approvals]


@router.get("/pending", response_model=list[ExpenseApprovalOut])
async def list_pending(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    approvals = await approval_service.list_pending_approvals(db, user.workspace_id)
    return [ExpenseApprovalOut.model_validate(a) for a in approvals]


@router.post("/submit/{transaction_id}", response_model=ExpenseApprovalOut, status_code=status.HTTP_201_CREATED)
async def submit_for_approval(
    transaction_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Submit a transaction for approval. Auto-matches the best policy."""
    from models import Transaction, TransactionType
    from sqlalchemy import select, and_
    txn = (await db.execute(select(Transaction).where(
        and_(Transaction.id == transaction_id, Transaction.workspace_id == user.workspace_id)
    ))).scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if txn.type != TransactionType.expense:
        raise HTTPException(status_code=400, detail="Only expense transactions can be submitted for approval")
    policy = await approval_service.find_matching_policy(db, user.workspace_id, float(txn.amount), txn.category)
    if not policy:
        raise HTTPException(status_code=400, detail="No matching approval policy found for this transaction amount/category")
    try:
        approval = await approval_service.submit_for_approval(db, user.workspace_id, transaction_id, user, policy)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.commit()
    await log_action(
        db,
        user,
        "approval.submit",
        "expense_approval",
        approval.id,
        new_value={"policy_id": str(policy.id), "status": approval.status.value},
    )
    approval = await approval_service.get_approval(db, user.workspace_id, approval.id)
    return ExpenseApprovalOut.model_validate(approval)


@router.post("/{approval_id}/approve", response_model=ExpenseApprovalOut)
async def approve(
    approval_id: uuid.UUID,
    data: ApprovalDecisionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    approval = await approval_service.get_approval(db, user.workspace_id, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    try:
        approval = await approval_service.approve_expense(db, approval, user.id, data.notes)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.commit()
    await log_action(db, user, "approval.approve", "expense_approval", approval.id)
    approval = await approval_service.get_approval(db, user.workspace_id, approval.id)
    return ExpenseApprovalOut.model_validate(approval)


@router.post("/{approval_id}/reject", response_model=ExpenseApprovalOut)
async def reject(
    approval_id: uuid.UUID,
    data: ApprovalDecisionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    approval = await approval_service.get_approval(db, user.workspace_id, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    try:
        approval = await approval_service.reject_expense(db, approval, user.id, data.rejection_reason)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.commit()
    await log_action(db, user, "approval.reject", "expense_approval", approval.id)
    approval = await approval_service.get_approval(db, user.workspace_id, approval.id)
    return ExpenseApprovalOut.model_validate(approval)
