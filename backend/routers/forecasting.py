"""
AI CFO — Forecasting Router (EXT-001)
Thin HTTP adapter; implementation injected via ForecastService Protocol.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_rls_db, get_forecast_service
from auth import get_current_user
from models import User
from schemas import ForecastResponse
from services.forecast_protocol import ForecastService

router = APIRouter()


@router.get("/", response_model=ForecastResponse)
async def get_forecast(
    months_ahead: int = Query(6, ge=1, le=24),
    scenario: str = Query("base", regex="^(optimistic|base|pessimistic)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
    forecast_svc: ForecastService = Depends(get_forecast_service),
):
    """Generate a cash flow forecast for the workspace."""
    return await forecast_svc.generate_forecast(
        db, user.workspace_id, months_ahead, scenario
    )
