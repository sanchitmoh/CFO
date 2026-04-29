"""
AI CFO — Audit Log Router (Feature D)
Read-only access to the audit trail with pagination and filtering.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_rls_db
from auth import get_current_user
from models import User, AuditLog
from schemas import AuditLogOut, PaginatedAuditLogs

router = APIRouter()


@router.get("/", response_model=PaginatedAuditLogs)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    entity_type: str | None = None,
    action: str | None = None,
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """List audit log entries with filtering and pagination."""
    ws_id = user.workspace_id
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    base_filter = and_(
        AuditLog.workspace_id == ws_id,
        AuditLog.created_at >= cutoff,
    )
    if entity_type:
        base_filter = and_(base_filter, AuditLog.entity_type == entity_type)
    if action:
        base_filter = and_(base_filter, AuditLog.action.ilike(f"%{action}%"))

    # Count
    count_q = await db.execute(
        select(func.count(AuditLog.id)).where(base_filter)
    )
    total = count_q.scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    result = await db.execute(
        select(AuditLog, User.email, User.full_name)
        .join(User, AuditLog.user_id == User.id)
        .where(base_filter)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )

    items = []
    for row in result:
        log_entry = row[0]
        items.append(AuditLogOut(
            id=log_entry.id,
            user_email=row[1],
            user_name=row[2],
            action=log_entry.action,
            entity_type=log_entry.entity_type,
            entity_id=log_entry.entity_id,
            old_value=log_entry.old_value,
            new_value=log_entry.new_value,
            created_at=log_entry.created_at,
        ))

    return PaginatedAuditLogs(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )
