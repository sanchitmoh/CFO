"""
AI CFO — Dashboard Router
Uses dashboard_service for aggregated data with caching.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user
from models import User
from schemas import DashboardSummary, CashFlowPoint, ExpenseBreakdownItem
from services.dashboard_service import get_dashboard_summary

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    months: int = Query(6, ge=1, le=24),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the aggregated dashboard summary for the current workspace."""
    return await get_dashboard_summary(db, user.workspace_id, months)
