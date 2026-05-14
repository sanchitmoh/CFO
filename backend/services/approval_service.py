"""
AI CFO — Expense Approval Service
Policy matching, approval workflows, and decision tracking.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import ApprovalPolicy, ApprovalStatus, ExpenseApproval, User
from services.budget_service import normalize_category_key, normalize_category_label


def _approval_query(ws_id: uuid.UUID):
    return (
        select(ExpenseApproval)
        .where(ExpenseApproval.workspace_id == ws_id)
        .options(
            selectinload(ExpenseApproval.transaction),
            selectinload(ExpenseApproval.policy),
            selectinload(ExpenseApproval.requester),
            selectinload(ExpenseApproval.approver),
        )
    )


async def list_policies(db: AsyncSession, ws_id: uuid.UUID) -> list[ApprovalPolicy]:
    return list((await db.execute(
        select(ApprovalPolicy).where(and_(ApprovalPolicy.workspace_id == ws_id, ApprovalPolicy.is_active.is_(True)))
        .order_by(ApprovalPolicy.min_amount))).scalars())


async def create_policy(db: AsyncSession, ws_id: uuid.UUID, data) -> ApprovalPolicy:
    categories = [normalize_category_label(category) for category in (data.categories or [])]
    auto_approve_roles = [str(role).strip().casefold() for role in (data.auto_approve_roles or []) if str(role).strip()]
    policy = ApprovalPolicy(
        workspace_id=ws_id, name=data.name,
        min_amount=Decimal(str(data.min_amount)),
        max_amount=Decimal(str(data.max_amount)) if data.max_amount is not None else None,
        required_approvers=data.required_approvers,
        auto_approve_roles=auto_approve_roles,
        categories=categories,
    )
    db.add(policy); await db.flush(); await db.refresh(policy); return policy


async def get_policy(db: AsyncSession, ws_id: uuid.UUID, pol_id: uuid.UUID) -> ApprovalPolicy | None:
    return (await db.execute(select(ApprovalPolicy).where(
        and_(ApprovalPolicy.id == pol_id, ApprovalPolicy.workspace_id == ws_id)))).scalar_one_or_none()


async def find_matching_policy(db: AsyncSession, ws_id: uuid.UUID, amount: float, category: str | None = None) -> ApprovalPolicy | None:
    """Find the best-matching approval policy for an expense."""
    policies = await list_policies(db, ws_id)
    normalized_category = normalize_category_key(category) if category else None
    for p in sorted(policies, key=lambda p: float(p.min_amount), reverse=True):
        min_a = float(p.min_amount)
        max_a = float(p.max_amount) if p.max_amount else float("inf")
        if min_a <= amount <= max_a:
            policy_categories = {normalize_category_key(item) for item in (p.categories or []) if item}
            if policy_categories and normalized_category and normalized_category not in policy_categories:
                continue
            return p
    return None


async def get_approval_by_transaction(db: AsyncSession, ws_id: uuid.UUID, txn_id: uuid.UUID) -> ExpenseApproval | None:
    result = await db.execute(
        _approval_query(ws_id).where(ExpenseApproval.transaction_id == txn_id)
    )
    return result.scalar_one_or_none()


async def submit_for_approval(
    db: AsyncSession,
    ws_id: uuid.UUID,
    txn_id: uuid.UUID,
    requester: User,
    policy: ApprovalPolicy,
) -> ExpenseApproval:
    existing = await get_approval_by_transaction(db, ws_id, txn_id)
    if existing:
        raise ValueError(f"Transaction already has an approval request with status '{existing.status.value}'")

    requester_role = str(getattr(requester.role, "value", requester.role or "")).casefold()
    auto_roles = {str(role).strip().casefold() for role in (policy.auto_approve_roles or []) if str(role).strip()}
    auto_approved = requester_role in auto_roles

    approval = ExpenseApproval(
        workspace_id=ws_id, transaction_id=txn_id,
        policy_id=policy.id,
        requested_by=requester.id,
        status=ApprovalStatus.auto_approved if auto_approved else ApprovalStatus.pending,
        approved_by=requester.id if auto_approved else None,
        approved_at=datetime.now(timezone.utc) if auto_approved else None,
        notes="Automatically approved by policy role" if auto_approved else None,
    )
    db.add(approval); await db.flush(); await db.refresh(approval); return approval


async def list_pending_approvals(db: AsyncSession, ws_id: uuid.UUID) -> list[ExpenseApproval]:
    result = await db.execute(
        _approval_query(ws_id).where(
            and_(ExpenseApproval.workspace_id == ws_id, ExpenseApproval.status == ApprovalStatus.pending)
        ).order_by(ExpenseApproval.created_at.desc())
    )
    return list(result.scalars())


async def list_all_approvals(db: AsyncSession, ws_id: uuid.UUID, status_filter: str | None = None) -> list[ExpenseApproval]:
    q = _approval_query(ws_id)
    if status_filter:
        q = q.where(ExpenseApproval.status == status_filter)
    return list((await db.execute(q.order_by(ExpenseApproval.created_at.desc()))).scalars())


async def get_approval(db: AsyncSession, ws_id: uuid.UUID, approval_id: uuid.UUID) -> ExpenseApproval | None:
    return (await db.execute(
        _approval_query(ws_id).where(ExpenseApproval.id == approval_id)
    )).scalar_one_or_none()


async def approve_expense(db: AsyncSession, approval: ExpenseApproval, approver_id: uuid.UUID, notes: str | None = None) -> ExpenseApproval:
    if approval.status != ApprovalStatus.pending:
        raise ValueError(f"Only pending approvals can be approved. Current status is '{approval.status.value}'")
    approval.status = ApprovalStatus.approved
    approval.approved_by = approver_id
    approval.approved_at = datetime.now(timezone.utc)
    approval.notes = notes
    await db.flush(); await db.refresh(approval); return approval


async def reject_expense(db: AsyncSession, approval: ExpenseApproval, approver_id: uuid.UUID, reason: str | None = None) -> ExpenseApproval:
    if approval.status != ApprovalStatus.pending:
        raise ValueError(f"Only pending approvals can be rejected. Current status is '{approval.status.value}'")
    approval.status = ApprovalStatus.rejected
    approval.approved_by = approver_id
    approval.approved_at = datetime.now(timezone.utc)
    approval.rejection_reason = reason
    await db.flush(); await db.refresh(approval); return approval
