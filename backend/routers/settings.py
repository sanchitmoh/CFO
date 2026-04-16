"""
AI CFO — Settings Router
Workspace settings, user profile, and team member management.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user
from models import User, Workspace, UserRole
from schemas import (
    UserOut, ProfileUpdate, WorkspaceOut, WorkspaceUpdate,
    InviteRequest, RoleUpdateRequest,
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
):
    """Invite a new team member (creates a placeholder user)."""
    if user.role not in (UserRole.owner, UserRole.admin):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Check for existing
    existing = await db.execute(
        select(User).where(
            and_(User.email == data.email, User.workspace_id == user.workspace_id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User already in workspace")

    new_user = User(
        workspace_id=user.workspace_id,
        email=data.email,
        full_name=data.full_name,
        role=UserRole(data.role),
    )
    db.add(new_user)
    await db.commit()

    await log_action(db, user, "team.invite", "user", new_user.id,
                     new_value={"email": data.email, "role": data.role})

    return {"status": "invited", "email": data.email}


@router.put("/team/{member_id}/role")
async def update_member_role(
    member_id: uuid.UUID,
    data: RoleUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
