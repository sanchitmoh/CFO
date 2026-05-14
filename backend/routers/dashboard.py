"""
AI CFO - Dashboard Router
Uses dashboard_service for aggregated data with caching.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from dependencies import get_rls_db
from models import Transaction, TransactionType, User, UserRole, Workspace
from schemas import DashboardSummary, HealthScoreResponse, InvestorSummaryResponse
from services.alert_engine import get_currency_symbol
from services.dashboard_service import get_dashboard_summary
from services.health_score_service import compute_health_score

router = APIRouter()

# HIGH-008: Roles permitted to view absolute financial figures
_INVESTOR_SUMMARY_ROLES = {UserRole.owner, UserRole.admin, UserRole.cfo, UserRole.investor}
_COGS_CATEGORY_ALIASES = ("cogs", "cost of goods sold", "cost of sales")


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    months: int = Query(6, ge=1, le=24),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """Get the aggregated dashboard summary for the current workspace."""
    return await get_dashboard_summary(db, user.workspace_id, months)


@router.get("/investor-summary", response_model=InvestorSummaryResponse)
async def investor_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_rls_db),
):
    """
    Read-only investor view with corrected operating metrics and context.

    HIGH-008: Gated to owner/admin/cfo/investor roles. Employee and
    accountant roles should not see absolute financial figures like
    exact revenue and cost structure.
    """
    if user.role not in _INVESTOR_SUMMARY_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to view investor summary",
        )

    summary = await get_dashboard_summary(db, user.workspace_id, 6)
    workspace = await db.scalar(select(Workspace).where(Workspace.id == user.workspace_id))
    health = await compute_health_score(db, user.workspace_id)

    date_row = (
        await db.execute(
            select(
                func.max(Transaction.date),
                func.min(Transaction.date),
            ).where(Transaction.workspace_id == user.workspace_id)
        )
    ).one_or_none()

    now = datetime.now(timezone.utc)
    latest_date = _coerce_utc(date_row[0] if date_row and date_row[0] else now)
    earliest_date = _coerce_utc(date_row[1] if date_row and date_row[1] else latest_date)
    window_start, _window_end = _resolve_reporting_window(
        latest_date,
        earliest_date,
        summary.period_months,
    )

    cogs_total = await db.scalar(
        select(func.sum(Transaction.amount)).where(
            and_(
                Transaction.workspace_id == user.workspace_id,
                Transaction.type == TransactionType.expense,
                Transaction.date >= window_start,
                func.lower(Transaction.category).in_(_COGS_CATEGORY_ALIASES),
            )
        )
    )

    return _build_investor_payload(
        summary=summary,
        workspace=workspace,
        health=health,
        latest_date=latest_date,
        earliest_date=earliest_date,
        cogs_total=float(cogs_total or 0.0),
        now=now,
    )


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _format_currency(amount: float, symbol: str) -> str:
    sign = "-" if amount < 0 else ""
    absolute = abs(amount)
    if absolute >= 1_000_000_000:
        return f"{sign}{symbol}{absolute / 1_000_000_000:,.1f}B"
    if absolute >= 1_000_000:
        return f"{sign}{symbol}{absolute / 1_000_000:,.1f}M"
    if absolute >= 1_000:
        return f"{sign}{symbol}{absolute / 1_000:,.0f}K"
    return f"{sign}{symbol}{absolute:,.0f}"


def _format_percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def _format_ratio(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}x"


def _pct_change(current: float, previous: float | None) -> float | None:
    if previous is None or previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100


def _format_delta(change: float | None) -> str:
    if change is None:
        return "N/A"
    return f"{change:+.1f}%"


def _humanize_slug(value: str | None) -> str:
    if not value:
        return "Unknown"
    return value.replace("_", " ").replace("-", " ").title()


def _health_label(score: float) -> str:
    if score >= 71:
        return "Good"
    if score >= 41:
        return "Caution"
    return "Critical"


def _resolve_reporting_window(
    latest_date: datetime,
    earliest_date: datetime,
    months: int,
) -> tuple[datetime, datetime]:
    cutoff = latest_date - timedelta(days=max(months, 1) * 30)
    if cutoff < earliest_date:
        cutoff = earliest_date
    return cutoff, latest_date


def _build_revenue_trend(summary: DashboardSummary) -> list[dict]:
    points: list[dict] = []
    for period, revenue, expenses in zip(
        summary.monthly_periods,
        summary.monthly_income,
        summary.monthly_expenses,
    ):
        month_date = datetime.strptime(period, "%Y-%m")
        points.append(
            {
                "month": month_date.strftime("%b"),
                "period": period,
                "revenue": revenue,
                "expenses": expenses,
                "net": revenue - expenses,
            }
        )

    active_points = [point for point in points if point["revenue"] or point["expenses"]]
    return active_points or points


def _dedupe_text(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def _build_investor_payload(
    summary: DashboardSummary,
    workspace: Workspace | None,
    health: HealthScoreResponse,
    latest_date: datetime,
    earliest_date: datetime,
    cogs_total: float,
    now: datetime,
) -> InvestorSummaryResponse:
    latest_date = _coerce_utc(latest_date)
    earliest_date = _coerce_utc(earliest_date)
    window_start, window_end = _resolve_reporting_window(
        latest_date,
        earliest_date,
        summary.period_months,
    )

    trend_points = _build_revenue_trend(summary)
    observed_months = len(trend_points) or max(summary.period_months, 1)
    stale_days = max((now.date() - latest_date.date()).days, 0)
    historical = stale_days > 60

    revenue = float(summary.total_income or 0.0)
    expenses = float(summary.total_expenses or 0.0)
    net_cash_flow = float(summary.net_cash_flow or 0.0)
    avg_monthly_expenses = expenses / max(observed_months, 1)
    coverage_ratio = (revenue / expenses) if expenses > 0 else None
    operating_margin = ((net_cash_flow / revenue) * 100) if revenue > 0 else None
    gross_margin = ((revenue - cogs_total) / revenue * 100) if revenue > 0 and cogs_total > 0 else None

    previous_point = trend_points[-2] if len(trend_points) >= 2 else None
    latest_point = trend_points[-1] if trend_points else None
    revenue_delta = _pct_change(
        latest_point["revenue"] if latest_point else 0.0,
        previous_point["revenue"] if previous_point else None,
    )
    expense_delta = _pct_change(
        latest_point["expenses"] if latest_point else 0.0,
        previous_point["expenses"] if previous_point else None,
    )

    top_category = summary.top_categories[0] if summary.top_categories else None
    top_share = ((top_category.amount / expenses) * 100) if top_category and expenses > 0 else 0.0

    company_name = workspace.name if workspace and workspace.name else "Your Company"
    industry = _humanize_slug(workspace.industry if workspace else None)
    currency = workspace.currency if workspace and workspace.currency else "USD"
    symbol = get_currency_symbol(currency)

    data_note = (
        f"Historical snapshot: latest uploaded transaction is from {latest_date:%d %b %Y}, "
        f"{stale_days} days behind today."
        if historical
        else f"Current through {latest_date:%d %b %Y}. Reporting window spans {observed_months} observed months."
    )

    health_score = round(float(health.overall_score))
    health_label = _health_label(health_score)

    if coverage_ratio is None:
        coverage_statement = "No expense base is available yet, so revenue coverage cannot be assessed."
    else:
        coverage_statement = f"Revenue covered {coverage_ratio:.2f}x of expenses."

    if top_category:
        concentration_statement = (
            f"{top_category.category} was the largest cost center at {top_share:.0f}% of total spend."
        )
    else:
        concentration_statement = "No expense categories are available yet."

    narrative_prefix = (
        f"Historical investor snapshot through {latest_date:%d %b %Y}."
        if historical
        else f"Investor snapshot through {latest_date:%d %b %Y}."
    )
    narrative = (
        f"{narrative_prefix} The business generated {_format_currency(revenue, symbol)} in revenue "
        f"against {_format_currency(expenses, symbol)} in expenses across the latest {observed_months} observed months. "
        f"{coverage_statement} {concentration_statement}"
    )

    metrics = [
        {
            "id": "revenue_window",
            "label": "Revenue in Window",
            "value": _format_currency(revenue, symbol),
            "delta": _format_delta(revenue_delta),
            "positive": (revenue_delta or 0) >= 0,
            "note": "Latest month vs previous observed month",
        },
        {
            "id": "avg_monthly_spend",
            "label": "Avg Monthly Spend",
            "value": _format_currency(avg_monthly_expenses, symbol),
            "delta": _format_delta(expense_delta),
            "positive": expense_delta is not None and expense_delta <= 0,
            "note": "Average operating spend across observed months",
        },
        {
            "id": "net_cash_flow",
            "label": "Net Cash Flow",
            "value": _format_currency(net_cash_flow, symbol),
            "delta": "",
            "positive": net_cash_flow >= 0,
            "note": "Revenue minus expenses in the reporting window",
        },
        {
            "id": "operating_margin",
            "label": "Operating Margin",
            "value": _format_percent(operating_margin),
            "delta": "",
            "positive": operating_margin is not None and operating_margin >= 0,
            "note": "Net cash flow divided by revenue",
        },
        {
            "id": "revenue_coverage",
            "label": "Revenue Coverage",
            "value": _format_ratio(coverage_ratio),
            "delta": "",
            "positive": coverage_ratio is not None and coverage_ratio >= 1,
            "note": "Revenue divided by total expenses",
        },
    ]

    kpis = [
        {
            "label": "Gross Margin",
            "value": _format_percent(gross_margin),
            "trend": "up" if gross_margin is not None and gross_margin >= 50 else "down" if gross_margin is not None else "neutral",
            "change": "Uses COGS-tagged expenses only" if gross_margin is not None else "No COGS-tagged spend found",
        },
        {
            "label": "Budget Utilization",
            "value": _format_percent(summary.budget_utilization),
            "trend": "up" if summary.budget_utilization <= 85 else "down",
            "change": "Budget discipline across active plans",
        },
        {
            "label": "Top Cost Concentration",
            "value": _format_percent(top_share if top_category else None),
            "trend": "down" if top_share >= 35 else "neutral",
            "change": top_category.category if top_category else "No dominant cost center",
        },
        {
            "label": "Transactions Reviewed",
            "value": f"{summary.transaction_count}",
            "trend": "neutral",
            "change": f"{observed_months} observed months",
        },
        {
            "label": "Health Score",
            "value": f"{health_score}/100",
            "trend": "up" if health_score >= 71 else "down" if health_score < 41 else "neutral",
            "change": f"{health.grade} · {_humanize_slug(health.stage)} stage",
        },
        {
            "label": "Data Freshness",
            "value": f"{stale_days}d",
            "trend": "down" if historical else "up",
            "change": "Historical" if historical else "Current",
        },
    ]

    highlights: list[str] = []
    if revenue > 0:
        highlights.append(
            f"{_format_currency(revenue, symbol)} revenue is available for review across {observed_months} observed months."
        )
    if health_score >= 71:
        highlights.append(
            f"Health score is {health_score}/100 ({health_label.lower()}) under the current stage-aware model."
        )
    if top_category and top_share <= 35:
        highlights.append(
            f"Expense mix is relatively diversified; {top_category.category} is the largest category at {top_share:.0f}% of spend."
        )
    if not highlights:
        highlights.append("The workspace has enough structured transaction history to support an investor snapshot.")

    risks: list[str] = []
    if historical:
        risks.append(
            f"Latest transaction activity is dated {latest_date:%d %b %Y}, so this page is a historical memo rather than a live board view."
        )
    if operating_margin is not None and operating_margin < 0:
        risks.append(
            f"Operating margin is {_format_percent(operating_margin)}, meaning the business spent more than it generated in the reporting window."
        )
    if coverage_ratio is not None and coverage_ratio < 1:
        risks.append(
            f"Revenue covered only {coverage_ratio:.2f}x of expenses, which suggests the current operating model is not self-funding."
        )
    if top_category and top_share >= 35:
        risks.append(
            f"{top_category.category} represents {top_share:.0f}% of total spend, creating concentration risk in one cost center."
        )
    if health_score < 41:
        risks.append(
            f"Composite health score is {health_score}/100, which falls in the critical range."
        )

    recommendations = _dedupe_text(
        [
            (
                f"Audit {top_category.category} first; it represents {top_share:.0f}% of total spend."
                if top_category
                else ""
            ),
            (
                "Upload more recent transactions before using this page for live investor updates or board materials."
                if historical
                else ""
            ),
            (
                "Reset the operating plan until revenue coverage moves above 1.0x."
                if coverage_ratio is not None and coverage_ratio < 1
                else ""
            ),
            (
                "Review pricing or cost-of-goods structure to improve gross margin."
                if gross_margin is not None and gross_margin < 40
                else ""
            ),
            (
                "Tighten budget controls around the highest-spend teams before adding new fixed costs."
                if summary.budget_utilization > 95
                else ""
            ),
            *health.recommendations,
        ]
    )[:4]

    expense_mix = [
        {
            "category": item.category,
            "amount": float(item.amount),
            "share_pct": round((float(item.amount) / expenses) * 100, 1) if expenses > 0 else 0.0,
        }
        for item in summary.top_categories
    ]

    return InvestorSummaryResponse(
        company={
            "name": company_name,
            "industry": industry,
            "currency": currency,
        },
        data_quality={
            "as_of": latest_date,
            "window_start": window_start,
            "window_end": window_end,
            "stale_days": stale_days,
            "observed_months": observed_months,
            "historical": historical,
            "note": data_note,
        },
        health_score=health_score,
        health_label=health_label,
        health_grade=health.grade,
        health_stage=health.stage,
        narrative=narrative,
        metrics=metrics,
        revenue_trend=trend_points,
        kpis=kpis,
        expense_mix=expense_mix,
        highlights=_dedupe_text(highlights)[:3],
        risks=_dedupe_text(risks)[:4],
        recommendations=recommendations or ["Upload financial data to generate investor guidance."],
        health_components=health.components,
    )
