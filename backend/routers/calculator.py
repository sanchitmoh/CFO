"""
AI CFO — Calculator Router (Feature B)
Thin HTTP adapter; logic lives in calculator_service.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user
from models import User
from schemas import AffordabilityRequest, AffordabilityResponse
from services.calculator_service import check_affordability

router = APIRouter()


@router.post("/affordability", response_model=AffordabilityResponse)
async def check_affordability_endpoint(
    req: AffordabilityRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyze whether the business can afford a proposed expense."""
    return await check_affordability(db, user.workspace_id, req)
