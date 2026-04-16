"""
AI CFO — Auth Router
Clerk-based authentication endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user
from models import User
from schemas import UserOut

router = APIRouter()


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    """Get the currently authenticated user's info."""
    return UserOut.model_validate(user)


@router.post("/sync")
async def sync_user(user: User = Depends(get_current_user)):
    """
    Sync endpoint — called after Clerk sign-in.
    The get_current_user dependency auto-provisions if needed.
    """
    return {
        "status": "synced",
        "user_id": str(user.id),
        "workspace_id": str(user.workspace_id),
    }
