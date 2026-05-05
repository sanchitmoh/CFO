"""
AI CFO — Calculator Service
Affordability analysis: "Can I afford this?" with AI-powered suggestions.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Transaction, TransactionType
from schemas import AffordabilityRequest, AffordabilityResponse


async def check_affordability(
    db: AsyncSession,
    workspace_id,
    req: AffordabilityRequest,
) -> AffordabilityResponse:
    """Analyze whether the business can afford a proposed expense."""
    # ── Anchor to latest transaction date (not wall-clock) ─────────
    # HIGH-002: Historical CSV imports may have dates far in the past.
    # Using now() as anchor would exclude all data.
    latest_row = await db.execute(
        select(func.max(Transaction.date))
        .where(Transaction.workspace_id == workspace_id)
    )
    latest_date = latest_row.scalar()
    anchor = latest_date if latest_date else datetime.now(timezone.utc)
    three_months_ago = anchor - timedelta(days=90)

    # ── Get last 3 months of income & expenses ───────────────────
    totals = await db.execute(
        select(Transaction.type, func.sum(Transaction.amount))
        .where(and_(
            Transaction.workspace_id == workspace_id,
            Transaction.date >= three_months_ago,
        ))
        .group_by(Transaction.type)
    )

    income_3m = 0.0
    expense_3m = 0.0
    for row in totals:
        if row[0] == TransactionType.income:
            income_3m = float(row[1] or 0)
        else:
            expense_3m = float(row[1] or 0)

    # ── Early return: no transaction data ─────────────────────────
    has_data = income_3m > 0 or expense_3m > 0
    if not has_data:
        return AffordabilityResponse(
            can_afford=False,
            current_runway_months=0.0,
            projected_runway_months=0.0,
            current_balance_3m=0.0,
            projected_balance_3m=-req.amount if req.frequency == "one_time" else -req.amount * 3,
            break_even_revenue=None,
            ai_suggestion=(
                f"📊 Insufficient data to evaluate '{req.expense_name}'. "
                f"We need at least 1 month of transaction history to provide "
                f"an accurate affordability analysis. Please connect a bank account "
                f"or upload transactions first."
            ),
        )

    net_3m = income_3m - expense_3m
    monthly_burn = expense_3m / 3 if expense_3m > 0 else 0
    monthly_income = income_3m / 3

    # ── Calculate impact ─────────────────────────────────────────
    if req.frequency == "monthly":
        extra_3m = req.amount * 3
    elif req.frequency == "annual":
        extra_3m = req.amount / 4
    else:  # one_time
        extra_3m = req.amount

    projected_3m = net_3m - extra_3m
    # When there's no burn, runway is effectively unlimited — cap at a
    # reasonable display value rather than leaking a raw sentinel.
    current_runway = net_3m / monthly_burn if monthly_burn > 0 else min(net_3m / 1, 99.0) if net_3m > 0 else 0.0
    new_burn = monthly_burn + (extra_3m / 3)
    projected_runway = net_3m / new_burn if new_burn > 0 else 0.0

    can_afford = projected_runway >= 3.0 and projected_3m > 0

    # ── Break-even revenue ───────────────────────────────────────
    break_even = None
    if not can_afford and monthly_income > 0:
        raw = (new_burn - monthly_income) * 3
        break_even = max(raw, 0)  # guard against negative break-even

    # ── AI Suggestion ────────────────────────────────────────────
    if can_afford and projected_runway > 6:
        suggestion = (
            f"✅ You can comfortably afford '{req.expense_name}'. "
            f"Your runway remains {projected_runway:.1f} months after this expense."
        )
    elif can_afford:
        suggestion = (
            f"⚠️ You can afford '{req.expense_name}', but it reduces your runway to "
            f"{projected_runway:.1f} months. Consider spreading the cost or finding "
            f"offsetting revenue."
        )
    else:
        if break_even is not None and break_even > 0:
            suggestion = (
                f"🚫 '{req.expense_name}' would reduce your runway to {projected_runway:.1f} months. "
                f"We recommend deferring this expense or increasing revenue by "
                f"${break_even:,.2f} over 3 months to break even."
            )
        else:
            suggestion = (
                f"🚫 '{req.expense_name}' would reduce your runway to {projected_runway:.1f} months. "
                f"Without recurring income, this expense is not sustainable. "
                f"We recommend establishing revenue before committing to this cost."
            )

    return AffordabilityResponse(
        can_afford=can_afford,
        current_runway_months=round(current_runway, 1),
        projected_runway_months=round(projected_runway, 1),
        current_balance_3m=round(net_3m, 2),
        projected_balance_3m=round(projected_3m, 2),
        break_even_revenue=round(break_even, 2) if break_even else None,
        ai_suggestion=suggestion,
    )
