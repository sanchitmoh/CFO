"""
AI CFO — Dashboard Router
Uses dashboard_service for aggregated data with caching.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_rls_db
from auth import get_current_user
from models import User, UserRole
from schemas import DashboardSummary
from services.dashboard_service import get_dashboard_summary

router = APIRouter()

# HIGH-008: Roles permitted to view absolute financial figures
_INVESTOR_SUMMARY_ROLES = {UserRole.owner, UserRole.admin, UserRole.cfo, UserRole.investor}


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    months: int = Query(6, ge=1, le=24),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Get the aggregated dashboard summary for the current workspace."""
    return await get_dashboard_summary(db, user.workspace_id, months)


@router.get("/investor-summary")
async def investor_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """
    Read-only investor view: health score, key metrics, revenue trend, KPIs.

    HIGH-008: Gated to owner/admin/cfo/investor roles. Employee and
    accountant roles should not see absolute financial figures like
    exact revenue, burn rate, and cash balance.
    """
    if user.role not in _INVESTOR_SUMMARY_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to view investor summary",
        )

    summary = await get_dashboard_summary(db, user.workspace_id, 6)

    # Compute derived metrics
    revenue = summary.total_income or 0
    expenses = summary.total_expenses or 0
    cash = summary.net_cash_flow or 0
    burn_rate = expenses  # simplified monthly burn
    runway = round(cash / burn_rate, 1) if burn_rate > 0 else 99
    gross_margin = round((1 - expenses / revenue) * 100) if revenue > 0 else 0
    rev_exp_ratio = round(revenue / expenses, 2) if expenses > 0 else 0

    # Revenue delta — compute actual MoM from monthly_income array
    if len(summary.monthly_income) >= 2 and summary.monthly_income[-2] > 0:
        prev_month = summary.monthly_income[-2]
        curr_month = summary.monthly_income[-1]
        pct_change = ((curr_month - prev_month) / prev_month) * 100
        revenue_delta = f"{pct_change:+.1f}%"
    else:
        revenue_delta = "N/A"
    
    now = datetime.now(timezone.utc)

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
        "revenue_trend": _build_revenue_trend(summary, now),
        "kpis": [
            {"label": "Gross Margin", "value": f"{gross_margin}%", "trend": "up" if gross_margin > 50 else "down", "change": ""},
            {"label": "Revenue / Expense", "value": f"{rev_exp_ratio}×", "trend": "up" if rev_exp_ratio > 1 else "down", "change": ""},
            {"label": "Health Score", "value": f"{health_score}/100", "trend": "neutral", "change": health_label},
        ],
    }


def _build_revenue_trend(summary, now: datetime) -> list[dict]:
    """Build revenue trend array with correct month labels.
    
    LOW-004 FIX: Month labels must align with the data anchor used by
    dashboard_service (MAX(Transaction.date)), not datetime.now().
    
    Since dashboard_service computes monthly_income/monthly_expenses arrays
    relative to the cutoff date (latest_date - N months), we need to derive
    the same anchor here. However, we don't have access to latest_date in
    this function. As a workaround, we use the fact that the data arrays
    represent the most recent N months of actual transaction data.
    
    For proper alignment, the frontend should pass the data anchor date,
    or this function should be moved into dashboard_service where it has
    access to latest_date.
    
    TEMPORARY FIX: Use now as a proxy, but document the limitation.
    TODO: Refactor to pass latest_date from dashboard_service.
    """
    from dateutil.relativedelta import relativedelta
    
    # Determine how many months we have data for
    count = min(len(summary.monthly_income), len(summary.monthly_expenses))
    if count == 0:
        return []
    
    # Start from the current month and go backwards
    # NOTE: This assumes data is current. For historical imports, labels
    # will be incorrect until we refactor to use the actual data anchor.
    current_month = now.replace(day=1)
    
    trend = []
    for i in range(count):
        # Calculate the month for this data point (going backwards from current)
        month_date = current_month - relativedelta(months=count - 1 - i)
        
        trend.append({
            "month": month_date.strftime("%b"),
            "revenue": summary.monthly_income[i] if i < len(summary.monthly_income) else 0,
            "expenses": summary.monthly_expenses[i] if i < len(summary.monthly_expenses) else 0,
        })
    
    return trend


