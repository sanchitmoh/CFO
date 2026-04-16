"""
AI CFO — Health Score Router
Computes a 0-100 financial health score from 4 components.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user
from models import User, Transaction, TransactionType, Budget
from schemas import HealthScoreResponse, ScoreComponent
from cache import cache_get, cache_set, make_cache_key

router = APIRouter()


@router.get("/", response_model=HealthScoreResponse)
async def get_health_score(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compute the financial health score for the workspace."""
    ws_id = user.workspace_id
    cache_key = make_cache_key("health_score", str(ws_id))

    cached = await cache_get(cache_key)
    if cached:
        return HealthScoreResponse(**cached)

    now = datetime.utcnow()
    three_months = now - timedelta(days=90)

    # ── Get income/expense totals ─────────────────────────────────
    totals = await db.execute(
        select(Transaction.type, func.sum(Transaction.amount))
        .where(and_(Transaction.workspace_id == ws_id, Transaction.date >= three_months))
        .group_by(Transaction.type)
    )

    income = 0.0
    expenses = 0.0
    for row in totals:
        if row[0] == TransactionType.income:
            income = float(row[1] or 0)
        else:
            expenses = float(row[1] or 0)

    monthly_burn = expenses / 3
    runway = (income - expenses) / monthly_burn if monthly_burn > 0 else 99

    # ── Component 1: Cash Flow (0-25) ────────────────────────────
    net = income - expenses
    if net > 0 and net / max(income, 1) > 0.2:
        cf_score = 25
        cf_status = "excellent"
        cf_desc = "Strong positive cash flow"
    elif net > 0:
        cf_score = 18
        cf_status = "good"
        cf_desc = "Positive but thin cash flow"
    elif net > -monthly_burn:
        cf_score = 10
        cf_status = "fair"
        cf_desc = "Negative cash flow, but manageable"
    else:
        cf_score = 5
        cf_status = "poor"
        cf_desc = "Significant negative cash flow"

    # ── Component 2: Runway (0-25) ────────────────────────────────
    if runway >= 12:
        rw_score = 25
        rw_status = "excellent"
        rw_desc = f"12+ month runway ({runway:.1f} months)"
    elif runway >= 6:
        rw_score = 18
        rw_status = "good"
        rw_desc = f"Healthy runway ({runway:.1f} months)"
    elif runway >= 3:
        rw_score = 10
        rw_status = "fair"
        rw_desc = f"Short runway ({runway:.1f} months) — reduce costs"
    else:
        rw_score = 3
        rw_status = "poor"
        rw_desc = f"Critical runway ({runway:.1f} months) — urgent action"

    # ── Component 3: Budget Adherence (0-25) ──────────────────────
    budget_q = await db.execute(
        select(func.sum(Budget.current_spend), func.sum(Budget.monthly_limit))
        .where(Budget.workspace_id == ws_id)
    )
    brow = budget_q.one_or_none()
    spent = float(brow[0] or 0) if brow else 0.0
    limit_total = float(brow[1] or 1) if brow else 1.0
    budget_pct = (spent / limit_total * 100) if limit_total > 0 else 0

    if budget_pct <= 80:
        ba_score = 25
        ba_status = "excellent"
        ba_desc = "Well within budget limits"
    elif budget_pct <= 95:
        ba_score = 18
        ba_status = "good"
        ba_desc = "Nearing budget limits"
    elif budget_pct <= 110:
        ba_score = 10
        ba_status = "fair"
        ba_desc = "Slightly over budget"
    else:
        ba_score = 3
        ba_status = "poor"
        ba_desc = f"Over budget by {budget_pct - 100:.0f}%"

    # ── Component 4: Income Diversity (0-25) ──────────────────────
    cats_q = await db.execute(
        select(func.count(func.distinct(Transaction.category)))
        .where(
            and_(
                Transaction.workspace_id == ws_id,
                Transaction.type == TransactionType.income,
                Transaction.date >= three_months,
            )
        )
    )
    income_sources = cats_q.scalar() or 0

    if income_sources >= 4:
        id_score = 25
        id_status = "excellent"
        id_desc = f"Diverse income ({income_sources} sources)"
    elif income_sources >= 2:
        id_score = 18
        id_status = "good"
        id_desc = f"Moderate diversification ({income_sources} sources)"
    elif income_sources == 1:
        id_score = 10
        id_status = "fair"
        id_desc = "Single income source — consider diversifying"
    else:
        id_score = 3
        id_status = "poor"
        id_desc = "No income recorded recently"

    overall = cf_score + rw_score + ba_score + id_score

    # Grade
    if overall >= 85:
        grade = "A"
    elif overall >= 70:
        grade = "B"
    elif overall >= 55:
        grade = "C"
    elif overall >= 40:
        grade = "D"
    else:
        grade = "F"

    # Recommendations
    recs = []
    if cf_score < 20:
        recs.append("Increase revenue or reduce expenses to improve cash flow")
    if rw_score < 20:
        recs.append("Build cash reserves to extend your runway to 6+ months")
    if ba_score < 20:
        recs.append("Review and adjust budgets to stay within limits")
    if id_score < 20:
        recs.append("Diversify income sources to reduce risk")

    result = HealthScoreResponse(
        overall_score=overall,
        grade=grade,
        components=[
            ScoreComponent(name="Cash Flow", score=cf_score, description=cf_desc, status=cf_status),
            ScoreComponent(name="Runway", score=rw_score, description=rw_desc, status=rw_status),
            ScoreComponent(name="Budget Adherence", score=ba_score, description=ba_desc, status=ba_status),
            ScoreComponent(name="Income Diversity", score=id_score, description=id_desc, status=id_status),
        ],
        recommendations=recs or ["Your financial health looks strong — keep it up!"],
        computed_at=now,
    )

    await cache_set(cache_key, result.model_dump(), ttl=600)
    return result
