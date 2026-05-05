"""
AI CFO — Settings Router
Workspace settings, user profile, and team member management.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_rls_db
from auth import get_current_user
from models import User, Workspace, UserRole
from schemas import (
    UserOut, ProfileUpdate, WorkspaceOut, WorkspaceUpdate,
    InviteRequest, RoleUpdateRequest,
    AlertSettingsUpdate, AlertSettingsOut,
)
from services.audit_service import log_action

router = APIRouter()


# ── Profile ───────────────────────────────────────────────────────

@router.get("/profile", response_model=UserOut)
async def get_profile(user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    return UserOut.model_validate(user)


@router.put("/profile", response_model=UserOut)
async def update_profile(
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Update the current user's profile."""
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url

    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


# ── Workspace ─────────────────────────────────────────────────────

@router.get("/workspace", response_model=WorkspaceOut)
async def get_workspace(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Get the current workspace settings."""
    result = await db.execute(
        select(Workspace).where(Workspace.id == user.workspace_id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceOut.model_validate(ws)


@router.put("/workspace", response_model=WorkspaceOut)
async def update_workspace(
    data: WorkspaceUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Update workspace settings (owner/admin only)."""
    if user.role not in (UserRole.owner, UserRole.admin):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    result = await db.execute(
        select(Workspace).where(Workspace.id == user.workspace_id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    old_values = {"name": ws.name, "industry": ws.industry, "currency": ws.currency}

    if data.name is not None:
        ws.name = data.name
    if data.industry is not None:
        ws.industry = data.industry
    if data.currency is not None:
        ws.currency = data.currency

    await db.commit()
    await db.refresh(ws)

    await log_action(db, user, "workspace.update", "workspace", ws.id,
                     old_value=old_values,
                     new_value={"name": ws.name, "industry": ws.industry, "currency": ws.currency})

    return WorkspaceOut.model_validate(ws)


# ── Team Members ──────────────────────────────────────────────────

@router.get("/team", response_model=list[UserOut])
async def list_team_members(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """List all team members in the workspace."""
    result = await db.execute(
        select(User)
        .where(User.workspace_id == user.workspace_id)
        .order_by(User.created_at)
    )
    return [UserOut.model_validate(u) for u in result.scalars()]


@router.post("/team/invite", status_code=status.HTTP_201_CREATED)
async def invite_member(
    data: InviteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """
    Invite a new team member.

    HIGH-002 FIX: Creates a pending invite record instead of a User row.
    User creation only happens via the Clerk SSO flow (auth.py provision_user_and_workspace).
    The invite record is stored in the audit log so it can be matched during SSO provisioning.
    """
    if user.role not in (UserRole.owner, UserRole.admin):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Check for existing user already in this workspace
    existing = await db.execute(
        select(User).where(
            and_(User.email == data.email, User.workspace_id == user.workspace_id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User already in workspace")

    # HIGH-002: Do NOT create a User row — that should only happen via Clerk SSO.
    # Instead, record the invite as an audit log entry with the intended role.
    # When the invited user signs up via Clerk, provision_user_and_workspace
    # can check for pending invites to assign the correct workspace and role.
    await log_action(
        db, user, "team.invite", "workspace", user.workspace_id,
        new_value={
            "email": data.email,
            "full_name": data.full_name,
            "role": data.role,
            "status": "pending",
        },
    )

    # TODO: Send invite email via Clerk Invitations API or transactional email service.
    # For now, the invite is tracked in audit_logs and can be matched during SSO provisioning.

    return {"status": "invited", "email": data.email, "note": "User will be created when they sign up via SSO"}


@router.put("/team/{member_id}/role")
async def update_member_role(
    member_id: uuid.UUID,
    data: RoleUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Update a team member's role."""
    if user.role not in (UserRole.owner, UserRole.admin):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    result = await db.execute(
        select(User).where(
            and_(User.id == member_id, User.workspace_id == user.workspace_id)
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    old_role = member.role.value
    member.role = UserRole(data.role)
    await db.commit()

    await log_action(db, user, "team.role_update", "user", member.id,
                     old_value={"role": old_role}, new_value={"role": data.role})

    return {"status": "updated", "role": data.role}


# ── Alert Settings ────────────────────────────────────────────────

_ALERT_DEFAULTS = AlertSettingsOut().model_dump()


@router.get("/alerts", response_model=AlertSettingsOut)
async def get_alert_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Get the workspace alert configuration."""
    result = await db.execute(
        select(Workspace).where(Workspace.id == user.workspace_id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    config = {**_ALERT_DEFAULTS, **(ws.alert_config or {})}
    return AlertSettingsOut(**config)


@router.put("/alerts", response_model=AlertSettingsOut)
async def update_alert_settings(
    data: AlertSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Update workspace alert settings (owner/admin only)."""
    if user.role not in (UserRole.owner, UserRole.admin):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    result = await db.execute(
        select(Workspace).where(Workspace.id == user.workspace_id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    existing = ws.alert_config or {}
    updates = data.model_dump(exclude_unset=True)
    merged = {**existing, **updates}
    ws.alert_config = merged

    await db.commit()
    await db.refresh(ws)

    await log_action(db, user, "settings.alerts_update", "workspace", ws.id,
                     old_value=existing, new_value=merged)

    full_config = {**_ALERT_DEFAULTS, **merged}
    return AlertSettingsOut(**full_config)
