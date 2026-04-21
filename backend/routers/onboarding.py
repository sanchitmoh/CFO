"""
AI CFO — Onboarding Router
Handles first-time user provisioning after Clerk sign-up.
Separated from auth to keep authentication pure (BUG-004).
"""
from fastapi import APIRouter, Depends

from auth import provision_user_and_workspace
from models import User
from schemas import UserOut

router = APIRouter()


@router.post("/provision", response_model=dict)
async def provision(
    result: tuple[User, bool] = Depends(provision_user_and_workspace),
):
    """
    Provision a workspace and user for a newly authenticated Clerk user.

    Idempotent — safe to call multiple times. Returns the user info
    and whether this was a first-time provisioning or an existing user.

    Frontend should call this once after first Clerk sign-in, before
    hitting any other API endpoints.
    """
    user, was_created = result
    return {
        "status": "provisioned" if was_created else "already_exists",
        "user": UserOut.model_validate(user).model_dump(mode="json"),
        "workspace_id": str(user.workspace_id),
    }
