"""
AI CFO — Alerts Router
CRUD for system and user-generated alerts.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_rls_db
from auth import get_current_user
from models import User, Alert, AlertSeverity
from schemas import AlertOut

router = APIRouter()


@router.get("/", response_model=list[AlertOut])
async def list_alerts(
    unread_only: bool = False,
    severity: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """List alerts for the workspace."""
    ws_id = user.workspace_id
    filters = [Alert.workspace_id == ws_id, Alert.is_dismissed.is_(False)]

    if unread_only:
        filters.append(Alert.is_read.is_(False))
    if severity:
        filters.append(Alert.severity == AlertSeverity(severity))

    result = await db.execute(
        select(Alert)
        .where(and_(*filters))
        .order_by(Alert.created_at.desc())
        .limit(limit)
    )
    return [AlertOut.model_validate(a) for a in result.scalars()]


@router.get("/count")
async def alert_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Get count of unread alerts."""
    result = await db.execute(
        select(func.count(Alert.id))
        .where(
            and_(
                Alert.workspace_id == user.workspace_id,
                Alert.is_read.is_(False),
                Alert.is_dismissed.is_(False),
            )
        )
    )
    return {"unread_count": result.scalar() or 0}


@router.put("/{alert_id}/read")
async def mark_read(
    alert_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Mark a single alert as read."""
    result = await db.execute(
        select(Alert).where(
            and_(Alert.id == alert_id, Alert.workspace_id == user.workspace_id)
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_read = True
    await db.commit()
    return {"status": "ok"}


@router.put("/read-all")
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Mark all alerts as read."""
    await db.execute(
        update(Alert)
        .where(
            and_(
                Alert.workspace_id == user.workspace_id,
                Alert.is_read.is_(False),
            )
        )
        .values(is_read=True)
    )
    await db.commit()
    return {"status": "ok"}


@router.put("/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Dismiss an alert permanently."""
    result = await db.execute(
        select(Alert).where(
            and_(Alert.id == alert_id, Alert.workspace_id == user.workspace_id)
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_dismissed = True
    alert.dismissed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "ok"}
