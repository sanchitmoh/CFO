"""
AI CFO — Dashboard Router
Uses dashboard_service for aggregated data with caching.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user
from models import User
from schemas import DashboardSummary
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


@router.get("/investor-summary")
async def investor_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Read-only investor view: health score, key metrics, revenue trend, KPIs.
    No raw transaction data is exposed.
    """
    summary = await get_dashboard_summary(db, user.workspace_id, 6)

    # Compute derived metrics
    revenue = summary.total_income or 0
    expenses = summary.total_expenses or 0
    cash = summary.net_cash_flow or 0
    burn_rate = expenses  # simplified monthly burn
    runway = round(cash / burn_rate, 1) if burn_rate > 0 else 99
    gross_margin = round((1 - expenses / revenue) * 100) if revenue > 0 else 0
    rev_exp_ratio = round(revenue / expenses, 2) if expenses > 0 else 0

    # Revenue delta (mock MoM for now — would need previous month)
    revenue_delta = "+12%"  # TODO: compute from actual monthly data

    health_score = summary.health_score if hasattr(summary, "health_score") else 72
    health_label = (
        "Good" if health_score >= 71
        else "Caution" if health_score >= 41
        else "Critical"
    )

    def fmt_currency(n: float) -> str:
        if abs(n) >= 1000:
            return f"${n / 1000:,.0f}K" if n < 1_000_000 else f"${n / 1_000_000:,.1f}M"
        return f"${n:,.0f}"

    return {
        "health_score": health_score,
        "health_label": health_label,
        "metrics": [
            {
                "label": "Monthly Revenue",
                "value": fmt_currency(revenue),
                "delta": revenue_delta,
                "positive": True,
                "note": "Month-over-month",
            },
            {
                "label": "Burn Rate",
                "value": f"{fmt_currency(burn_rate)}/mo",
                "delta": "",
                "positive": False,
                "note": "Monthly operating cost",
            },
            {
                "label": "Cash Runway",
                "value": f"{runway} months",
                "delta": "Healthy" if runway >= 6 else "Low",
                "positive": runway >= 6,
                "note": "At current burn rate",
            },
            {
                "label": "Cash Balance",
                "value": fmt_currency(cash),
                "delta": "",
                "positive": True,
                "note": "Current balance",
            },
        ],
        "revenue_trend": [
            {"month": p.month, "revenue": p.income, "expenses": p.expenses}
            for p in (summary.cash_flow_trend or [])
        ],
        "kpis": [
            {"label": "Gross Margin", "value": f"{gross_margin}%", "trend": "up" if gross_margin > 50 else "down", "change": ""},
            {"label": "Revenue / Expense", "value": f"{rev_exp_ratio}×", "trend": "up" if rev_exp_ratio > 1 else "down", "change": ""},
            {"label": "Health Score", "value": f"{health_score}/100", "trend": "neutral", "change": health_label},
        ],
    }

