"""
AI CFO — Health Score Router
Thin HTTP adapter; logic lives in health_score_service.
Supports ML-004 stage override via query param.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user
from models import User
from schemas import HealthScoreResponse
from services.health_score_service import compute_health_score

router = APIRouter()


@router.get("/", response_model=HealthScoreResponse)
async def get_health_score(
    stage: str | None = Query(
        None,
        description="Business stage override: early, growth, or mature. Auto-detected if omitted.",
        pattern="^(early|growth|mature)$",
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compute the financial health score for the workspace."""
    return await compute_health_score(db, user.workspace_id, stage_override=stage)
