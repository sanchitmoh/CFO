"""
AI CFO - Calculator Service
Affordability analysis based on actual cash position, recent net burn, and 3-month projections.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Transaction, TransactionType, Workspace
from schemas import AffordabilityRequest, AffordabilityResponse
from services.alert_engine import get_currency_symbol

ANALYSIS_MONTHS = 3
RUNWAY_CAP_MONTHS = 99.0


def _extract_totals(rows) -> tuple[float, float]:
    income = 0.0
    expense = 0.0
    for row in rows:
        if row[0] == TransactionType.income:
            income = float(row[1] or 0)
        else:
            expense = float(row[1] or 0)
    return income, expense


def _recurring_monthly_cost(amount: float, frequency: str) -> float:
    if frequency == "monthly":
        return amount
    if frequency == "annual":
        return amount / 12
    return 0.0


def _upfront_cost(amount: float, frequency: str) -> float:
    return amount if frequency == "one_time" else 0.0


def _runway_months(cash_balance: float, monthly_net_flow: float) -> float:
    if cash_balance <= 0:
        return 0.0
    if monthly_net_flow >= 0:
        return RUNWAY_CAP_MONTHS
    return min(cash_balance / abs(monthly_net_flow), RUNWAY_CAP_MONTHS)


def _build_recommendation(
    req: AffordabilityRequest,
    can_afford: bool,
    projected_runway: float,
    projected_balance_3m: float,
    break_even: float | None,
    sym: str,
) -> str:
    subject = "this hire" if req.is_hire else f"'{req.expense_name}'"

    if can_afford and projected_runway > 6:
        return (
            f"Affordable: {subject} keeps your projected runway at "
            f"{projected_runway:.1f} months with a 3-month ending cash position of "
            f"{sym}{projected_balance_3m:,.2f}."
        )

    if can_afford:
        return (
            f"Caution: {subject} is affordable, but it compresses projected runway to "
            f"{projected_runway:.1f} months. Monitor burn closely over the next quarter."
        )

    if break_even is not None and break_even > 0:
        return (
            f"Not affordable: {subject} would leave an estimated 3-month cash gap of "
            f"{sym}{abs(projected_balance_3m):,.2f}. You would need "
            f"{sym}{break_even:,.2f} of additional revenue over 3 months to stay cash-neutral."
        )

    return (
        f"Not affordable: {subject} would keep the business below a sustainable cash threshold. "
        f"Reduce the cost, defer the spend, or increase recurring revenue before committing."
    )


def _calculate_affordability_response(
    current_cash_balance: float,
    income_3m: float,
    expense_3m: float,
    req: AffordabilityRequest,
    sym: str,
) -> AffordabilityResponse:
    current_monthly_income = income_3m / ANALYSIS_MONTHS
    current_monthly_expense = expense_3m / ANALYSIS_MONTHS
    current_monthly_net = current_monthly_income - current_monthly_expense

    recurring_monthly_cost = _recurring_monthly_cost(req.amount, req.frequency)
    upfront_cost = _upfront_cost(req.amount, req.frequency)
    projected_cash_now = current_cash_balance - upfront_cost
    projected_monthly_net = current_monthly_net - recurring_monthly_cost

    current_balance_3m = current_cash_balance + current_monthly_net * ANALYSIS_MONTHS
    projected_balance_3m = projected_cash_now + projected_monthly_net * ANALYSIS_MONTHS

    current_runway = _runway_months(current_cash_balance, current_monthly_net)
    projected_runway = _runway_months(projected_cash_now, projected_monthly_net)

    can_afford = (
        projected_cash_now >= 0
        and projected_balance_3m >= 0
        and projected_runway >= ANALYSIS_MONTHS
    )

    break_even = None
    if not can_afford:
        break_even = max(-projected_balance_3m, 0.0)

    suggestion = _build_recommendation(
        req=req,
        can_afford=can_afford,
        projected_runway=projected_runway,
        projected_balance_3m=projected_balance_3m,
        break_even=break_even,
        sym=sym,
    )

    return AffordabilityResponse(
        can_afford=can_afford,
        current_runway_months=round(current_runway, 1),
        projected_runway_months=round(projected_runway, 1),
        current_balance_3m=round(current_balance_3m, 2),
        projected_balance_3m=round(projected_balance_3m, 2),
        break_even_revenue=round(break_even, 2) if break_even is not None else None,
        ai_suggestion=suggestion,
    )


async def check_affordability(
    db: AsyncSession,
    workspace_id,
    req: AffordabilityRequest,
) -> AffordabilityResponse:
    """Analyze whether the business can afford a proposed expense."""
    ws = await db.get(Workspace, workspace_id)
    sym = get_currency_symbol(ws.currency if ws else "USD")

    latest_row = await db.execute(
        select(func.max(Transaction.date)).where(Transaction.workspace_id == workspace_id)
    )
    latest_date = latest_row.scalar()
    anchor = latest_date if latest_date else datetime.now(timezone.utc)
    three_months_ago = anchor - timedelta(days=90)

    recent_totals = await db.execute(
        select(Transaction.type, func.sum(Transaction.amount))
        .where(
            and_(
                Transaction.workspace_id == workspace_id,
                Transaction.date >= three_months_ago,
            )
        )
        .group_by(Transaction.type)
    )
    income_3m, expense_3m = _extract_totals(recent_totals)

    all_time_totals = await db.execute(
        select(Transaction.type, func.sum(Transaction.amount))
        .where(Transaction.workspace_id == workspace_id)
        .group_by(Transaction.type)
    )
    total_income, total_expense = _extract_totals(all_time_totals)
    current_cash_balance = total_income - total_expense

    if income_3m <= 0 and expense_3m <= 0:
        recurring_monthly_cost = _recurring_monthly_cost(req.amount, req.frequency)
        upfront_cost = _upfront_cost(req.amount, req.frequency)
        projected_balance_3m = -upfront_cost - recurring_monthly_cost * ANALYSIS_MONTHS
        return AffordabilityResponse(
            can_afford=False,
            current_runway_months=0.0,
            projected_runway_months=0.0,
            current_balance_3m=0.0,
            projected_balance_3m=round(projected_balance_3m, 2),
            break_even_revenue=None,
            ai_suggestion=(
                f"Insufficient data: '{req.expense_name}' cannot be evaluated yet. "
                f"Connect a bank account or upload at least one month of transactions for a cash-based analysis."
            ),
        )

    return _calculate_affordability_response(
        current_cash_balance=current_cash_balance,
        income_3m=income_3m,
        expense_3m=expense_3m,
        req=req,
        sym=sym,
    )
