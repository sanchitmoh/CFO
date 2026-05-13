"""
AI CFO — Health Score Service (ML-004)
Stage-aware weighted scoring with adaptive component weights.

Weights adjust based on business stage:
  - Early: Runway-heavy (survival focus)
  - Growth: Revenue growth emphasis
  - Mature: Budget discipline + growth balance
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Transaction, TransactionType
from schemas import HealthScoreResponse, ScoreComponent
from cache import cache_get, cache_set, make_versioned_cache_key
from services.budget_service import get_budget_totals


# ═══════════════════════════════════════════════════════════════════
# ML-004 — Stage-Aware Weight Configuration
# ═══════════════════════════════════════════════════════════════════

WEIGHTS_BY_STAGE = {
    "early":  {"cash_flow": 0.15, "runway": 0.50, "budget": 0.10, "diversity": 0.25},
    "growth": {"cash_flow": 0.20, "runway": 0.30, "budget": 0.20, "diversity": 0.30},
    "mature": {"cash_flow": 0.25, "runway": 0.20, "budget": 0.35, "diversity": 0.20},
}

MAX_COMPONENT_SCORE = 100  # Each component scores 0-100, then weighted


def detect_business_stage(
    runway: float,
    monthly_revenue: float,
    months_of_data: int = 3,
) -> str:
    """
    Auto-detect business stage from financial indicators.

    - Early: <6 months runway OR <$5k monthly revenue
    - Growth: 6-18 months runway AND $5k-$50k monthly revenue
    - Mature: 18+ months runway OR >$50k monthly revenue
    """
    if runway < 6 or monthly_revenue < 5000:
        return "early"
    elif runway >= 18 or monthly_revenue >= 50000:
        return "mature"
    else:
        return "growth"


# ═══════════════════════════════════════════════════════════════════
# Component Scoring (0–100 scale for each)
# ═══════════════════════════════════════════════════════════════════

def _score_cash_flow(net: float, income: float, monthly_burn: float) -> tuple[int, str, str]:
    """0–100 for cash-flow health."""
    if income == 0 and net == 0:
        return 50, "neutral", "No financial data available"
    if net > 0 and net / max(income, 1) > 0.2:
        return 100, "excellent", "Strong positive cash flow"
    if net > 0:
        return 72, "good", "Positive but thin cash flow"
    if net > -monthly_burn:
        return 40, "fair", "Negative cash flow, but manageable"
    return 15, "poor", "Significant negative cash flow"


def _score_runway(runway: float) -> tuple[int, str, str]:
    """0–100 for runway length."""
    if runway >= 18:
        return 100, "excellent", f"18+ month runway ({runway:.1f} months)"
    if runway >= 12:
        return 85, "excellent", f"12+ month runway ({runway:.1f} months)"
    if runway >= 6:
        return 72, "good", f"Healthy runway ({runway:.1f} months)"
    if runway >= 3:
        return 40, "fair", f"Short runway ({runway:.1f} months) — reduce costs"
    return 12, "poor", f"Critical runway ({runway:.1f} months) — urgent action"


def _score_budget(budget_pct: float) -> tuple[int, str, str]:
    """0–100 for budget adherence."""
    if budget_pct <= 70:
        return 100, "excellent", "Well within budget limits"
    if budget_pct <= 85:
        return 80, "good", "On track with budgets"
    if budget_pct <= 95:
        return 60, "good", "Nearing budget limits"
    if budget_pct <= 110:
        return 35, "fair", "Slightly over budget"
    return 10, "poor", f"Over budget by {budget_pct - 100:.0f}%"


def _score_diversity(sources: int) -> tuple[int, str, str]:
    """0–100 for income diversity."""
    if sources >= 5:
        return 100, "excellent", f"Highly diverse income ({sources} sources)"
    if sources >= 3:
        return 80, "good", f"Good diversification ({sources} sources)"
    if sources >= 2:
        return 60, "good", f"Moderate diversification ({sources} sources)"
    if sources == 1:
        return 35, "fair", "Single income source — consider diversifying"
    return 10, "poor", "No income recorded recently"


# ═══════════════════════════════════════════════════════════════════
# Main Computation
# ═══════════════════════════════════════════════════════════════════

async def compute_health_score(
    db: AsyncSession,
    workspace_id,
    stage_override: str | None = None,
) -> HealthScoreResponse:
    """
    Compute the composite financial health score with stage-aware weights.

    Args:
        stage_override: "early", "growth", or "mature". Auto-detected if None.
    """
    cache_key = await make_versioned_cache_key("health_score", str(workspace_id))

    cached = await cache_get(cache_key)
    if cached:
        return HealthScoreResponse(**cached)

    now = datetime.now(timezone.utc)
    three_months = now - timedelta(days=90)

    # ── Income / expense totals ──────────────────────────────────
    totals = await db.execute(
        select(Transaction.type, func.sum(Transaction.amount))
        .where(and_(Transaction.workspace_id == workspace_id, Transaction.date >= three_months))
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
    monthly_revenue = income / 3
    net = income - expenses
    runway = net / monthly_burn if monthly_burn > 0 else 99

    # ── ML-004: Detect or use overridden stage ────────────────────
    stage = stage_override or detect_business_stage(runway, monthly_revenue)
    weights = WEIGHTS_BY_STAGE[stage]

    # ── Score each component (0-100 scale) ────────────────────────
    cf_score, cf_status, cf_desc = _score_cash_flow(net, income, monthly_burn)
    rw_score, rw_status, rw_desc = _score_runway(runway)

    # Budget adherence
    spent, limit_total = await get_budget_totals(db, workspace_id)
    budget_pct = (spent / limit_total * 100) if limit_total > 0 else 0
    ba_score, ba_status, ba_desc = _score_budget(budget_pct)

    # Income diversity
    cats_q = await db.execute(
        select(func.count(func.distinct(Transaction.category)))
        .where(and_(
            Transaction.workspace_id == workspace_id,
            Transaction.type == TransactionType.income,
            Transaction.date >= three_months,
        ))
    )
    income_sources = cats_q.scalar() or 0
    id_score, id_status, id_desc = _score_diversity(income_sources)

    # ── Weighted overall score ────────────────────────────────────
    overall = round(
        cf_score * weights["cash_flow"]
        + rw_score * weights["runway"]
        + ba_score * weights["budget"]
        + id_score * weights["diversity"]
    )
    overall = max(0, min(100, overall))

    # Grade
    grade = (
        "A" if overall >= 85 else
        "B" if overall >= 70 else
        "C" if overall >= 55 else
        "D" if overall >= 40 else "F"
    )

    # Recommendations — weighted by stage importance
    recs = []
    component_scores = [
        ("cash_flow", cf_score), ("runway", rw_score),
        ("budget", ba_score), ("diversity", id_score),
    ]
    # Sort by impact: low-scoring components with high weight first
    component_scores.sort(key=lambda c: c[1] * weights[c[0]])

    rec_map = {
        "cash_flow": "Increase revenue or reduce expenses to improve cash flow",
        "runway": "Build cash reserves to extend your runway to 6+ months",
        "budget": "Review and adjust budgets to stay within limits",
        "diversity": "Diversify income sources to reduce risk",
    }
    for comp_name, comp_score in component_scores:
        if comp_score < 60:
            recs.append(rec_map[comp_name])

    # Display weights as percentages in component descriptions
    result = HealthScoreResponse(
        overall_score=overall,
        grade=grade,
        stage=stage,
        components=[
            ScoreComponent(
                name="Cash Flow",
                score=round(cf_score * weights["cash_flow"]),
                description=f"{cf_desc} (weight: {weights['cash_flow']:.0%})",
                status=cf_status,
            ),
            ScoreComponent(
                name="Runway",
                score=round(rw_score * weights["runway"]),
                description=f"{rw_desc} (weight: {weights['runway']:.0%})",
                status=rw_status,
            ),
            ScoreComponent(
                name="Budget Adherence",
                score=round(ba_score * weights["budget"]),
                description=f"{ba_desc} (weight: {weights['budget']:.0%})",
                status=ba_status,
            ),
            ScoreComponent(
                name="Income Diversity",
                score=round(id_score * weights["diversity"]),
                description=f"{id_desc} (weight: {weights['diversity']:.0%})",
                status=id_status,
            ),
        ],
        recommendations=recs or ["Your financial health looks strong — keep it up!"],
        computed_at=now,
    )

    await cache_set(cache_key, result.model_dump(), ttl=600)
    return result
