"""
AI CFO — Forecasting Router
Thin HTTP adapter; logic lives in forecast_service.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user
from models import User
from schemas import ForecastResponse
from services.forecast_service import generate_forecast

router = APIRouter()


@router.get("/", response_model=ForecastResponse)
async def get_forecast(
    months_ahead: int = Query(6, ge=1, le=24),
    scenario: str = Query("base", regex="^(optimistic|base|pessimistic)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a cash flow forecast for the workspace."""
    return await generate_forecast(db, user.workspace_id, months_ahead, scenario)
