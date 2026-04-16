"""
AI CFO — Audit Service
Logs all user actions for compliance and traceability.
"""
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models import AuditLog, User


async def log_action(
    db: AsyncSession,
    user: User,
    action: str,
    entity_type: str,
    entity_id: Optional[uuid.UUID] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Create an audit log entry."""
    entry = AuditLog(
        workspace_id=user.workspace_id,
        user_id=user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.commit()
    return entry
