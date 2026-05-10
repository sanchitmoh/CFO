"""
AI CFO — Expense Approval Service
Policy matching, approval workflows, and decision tracking.
"""
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import ApprovalPolicy, ExpenseApproval, Transaction, ApprovalStatus, User

logger = logging.getLogger(__name__)


async def list_policies(db: AsyncSession, ws_id: uuid.UUID) -> list[ApprovalPolicy]:
    return list((await db.execute(
        select(ApprovalPolicy).where(and_(ApprovalPolicy.workspace_id == ws_id, ApprovalPolicy.is_active.is_(True)))
        .order_by(ApprovalPolicy.min_amount))).scalars())


async def create_policy(db: AsyncSession, ws_id: uuid.UUID, data) -> ApprovalPolicy:
    policy = ApprovalPolicy(
        workspace_id=ws_id, name=data.name,
        min_amount=Decimal(str(data.min_amount)),
        max_amount=Decimal(str(data.max_amount)) if data.max_amount else None,
        required_approvers=data.required_approvers,
        auto_approve_roles=data.auto_approve_roles, categories=data.categories,
    )
    db.add(policy); await db.flush(); await db.refresh(policy); return policy


async def get_policy(db: AsyncSession, ws_id: uuid.UUID, pol_id: uuid.UUID) -> ApprovalPolicy | None:
    return (await db.execute(select(ApprovalPolicy).where(
        and_(ApprovalPolicy.id == pol_id, ApprovalPolicy.workspace_id == ws_id)))).scalar_one_or_none()


async def find_matching_policy(db: AsyncSession, ws_id: uuid.UUID, amount: float, category: str | None = None) -> ApprovalPolicy | None:
    """Find the best-matching approval policy for an expense."""
    policies = await list_policies(db, ws_id)
    for p in sorted(policies, key=lambda p: float(p.min_amount), reverse=True):
        min_a = float(p.min_amount)
        max_a = float(p.max_amount) if p.max_amount else float("inf")
        if min_a <= amount <= max_a:
            if p.categories and category and category not in p.categories:
                continue
            return p
    return None


async def submit_for_approval(db: AsyncSession, ws_id: uuid.UUID, txn_id: uuid.UUID, user_id: uuid.UUID, policy_id: uuid.UUID) -> ExpenseApproval:
    approval = ExpenseApproval(
        workspace_id=ws_id, transaction_id=txn_id,
        policy_id=policy_id, requested_by=user_id,
    )
    db.add(approval); await db.flush(); await db.refresh(approval); return approval


async def list_pending_approvals(db: AsyncSession, ws_id: uuid.UUID) -> list[ExpenseApproval]:
    result = await db.execute(
        select(ExpenseApproval).where(
            and_(ExpenseApproval.workspace_id == ws_id, ExpenseApproval.status == ApprovalStatus.pending)
        ).order_by(ExpenseApproval.created_at.desc())
    )
    return list(result.scalars())


async def list_all_approvals(db: AsyncSession, ws_id: uuid.UUID, status_filter: str | None = None) -> list[ExpenseApproval]:
    q = select(ExpenseApproval).where(ExpenseApproval.workspace_id == ws_id)
    if status_filter:
        q = q.where(ExpenseApproval.status == status_filter)
    return list((await db.execute(q.order_by(ExpenseApproval.created_at.desc()))).scalars())


async def get_approval(db: AsyncSession, ws_id: uuid.UUID, approval_id: uuid.UUID) -> ExpenseApproval | None:
    return (await db.execute(select(ExpenseApproval).where(
        and_(ExpenseApproval.id == approval_id, ExpenseApproval.workspace_id == ws_id)))).scalar_one_or_none()


async def approve_expense(db: AsyncSession, approval: ExpenseApproval, approver_id: uuid.UUID, notes: str | None = None) -> ExpenseApproval:
    approval.status = ApprovalStatus.approved
    approval.approved_by = approver_id
    approval.approved_at = datetime.now(timezone.utc)
    approval.notes = notes
    await db.flush(); await db.refresh(approval); return approval


async def reject_expense(db: AsyncSession, approval: ExpenseApproval, approver_id: uuid.UUID, reason: str | None = None) -> ExpenseApproval:
    approval.status = ApprovalStatus.rejected
    approval.approved_by = approver_id
    approval.approved_at = datetime.now(timezone.utc)
    approval.rejection_reason = reason
    await db.flush(); await db.refresh(approval); return approval
