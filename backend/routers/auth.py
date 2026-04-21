"""
AI CFO — Auth Router
Clerk-based authentication endpoints.
"""
from fastapi import APIRouter, Depends

from auth import get_current_user, provision_user_and_workspace
from models import User
from schemas import UserOut

router = APIRouter()


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    """Get the currently authenticated user's info."""
    return UserOut.model_validate(user)


@router.post("/sync")
async def sync_user(
    result: tuple[User, bool] = Depends(provision_user_and_workspace),
):
    """
    Sync endpoint — called after Clerk sign-in.
    Provisions workspace + user on first call, no-ops on subsequent calls.
    """
    user, was_created = result
    return {
        "status": "provisioned" if was_created else "synced",
        "user_id": str(user.id),
        "workspace_id": str(user.workspace_id),
    }

