"""
AI CFO — Cash Flow Scenario Planning Service
Scenario CRUD, comparison, sensitivity analysis, Monte Carlo simulation,
industry templates, and collaborative sharing.
"""
import uuid
import logging
import random
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Scenario, SensitivityAnalysis, Transaction, TransactionType, ScenarioShare
from schemas import (
    ScenarioCreate, ScenarioUpdate, ScenarioAssumptions,
    ScenarioOut, ScenarioComparisonResponse, ScenarioTemplate,
    SensitivityRequest, SensitivityResponse,
    MonteCarloRequest, MonteCarloResponse,
    ScenarioShareCreate, ScenarioShareOut,
)

logger = logging.getLogger(__name__)
MAX_SCENARIOS = 12


# ── Industry Templates ─────────────────────────────────────────────

INDUSTRY_TEMPLATES: list[dict] = [
    {
        "id": "saas_startup",
        "name": "SaaS Startup",
        "description": "High growth, moderate churn, heavy hiring. Typical for Series A/B SaaS companies.",
        "industry": "Technology / SaaS",
        "assumptions": {
            "revenue_growth_pct": 15.0,
            "expense_change_pct": 10.0,
            "new_monthly_revenue": 0.0,
            "removed_monthly_expense": 0.0,
            "one_time_income": 0.0,
            "one_time_expense": 0.0,
            "headcount_change": 5,
            "avg_salary_per_head": 80000.0,
            "customer_churn_pct": 3.0,
            "pricing_change_pct": 0.0,
            "tax_rate_pct": 25.0,
            "capex_monthly": 5000.0,
            "loan_repayment_monthly": 0.0,
            "seasonal_dip_months": [],
        },
    },
    {
        "id": "retail_ecommerce",
        "name": "Retail / E-Commerce",
        "description": "Seasonal revenue, high COGS, inventory-driven. Peaks in Q4.",
        "industry": "Retail",
        "assumptions": {
            "revenue_growth_pct": 8.0,
            "expense_change_pct": 6.0,
            "new_monthly_revenue": 0.0,
            "removed_monthly_expense": 0.0,
            "one_time_income": 0.0,
            "one_time_expense": 0.0,
            "headcount_change": 2,
            "avg_salary_per_head": 40000.0,
            "customer_churn_pct": 5.0,
            "pricing_change_pct": 0.0,
            "tax_rate_pct": 30.0,
            "capex_monthly": 3000.0,
            "loan_repayment_monthly": 5000.0,
            "seasonal_dip_months": [1, 2, 6, 7],
        },
    },
    {
        "id": "professional_services",
        "name": "Professional Services",
        "description": "Stable headcount-driven revenue. Consulting, legal, accounting firms.",
        "industry": "Services",
        "assumptions": {
            "revenue_growth_pct": 5.0,
            "expense_change_pct": 3.0,
            "new_monthly_revenue": 0.0,
            "removed_monthly_expense": 0.0,
            "one_time_income": 0.0,
            "one_time_expense": 0.0,
            "headcount_change": 1,
            "avg_salary_per_head": 70000.0,
            "customer_churn_pct": 2.0,
            "pricing_change_pct": 3.0,
            "tax_rate_pct": 30.0,
            "capex_monthly": 1000.0,
            "loan_repayment_monthly": 0.0,
            "seasonal_dip_months": [12],
        },
    },
    {
        "id": "manufacturing",
        "name": "Manufacturing",
        "description": "High capex, moderate growth, equipment-intensive operations.",
        "industry": "Manufacturing",
        "assumptions": {
            "revenue_growth_pct": 6.0,
            "expense_change_pct": 4.0,
            "new_monthly_revenue": 0.0,
            "removed_monthly_expense": 0.0,
            "one_time_income": 0.0,
            "one_time_expense": 50000.0,
            "headcount_change": 3,
            "avg_salary_per_head": 45000.0,
            "customer_churn_pct": 1.0,
            "pricing_change_pct": 2.0,
            "tax_rate_pct": 25.0,
            "capex_monthly": 25000.0,
            "loan_repayment_monthly": 15000.0,
            "seasonal_dip_months": [],
        },
    },
    {
        "id": "early_stage",
        "name": "Early-Stage Startup",
        "description": "Pre-revenue or low-revenue, burn-rate focused, seeking product-market fit.",
        "industry": "Startup",
        "assumptions": {
            "revenue_growth_pct": 0.0,
            "expense_change_pct": 5.0,
            "new_monthly_revenue": 5000.0,
            "removed_monthly_expense": 0.0,
            "one_time_income": 0.0,
            "one_time_expense": 0.0,
            "headcount_change": 2,
            "avg_salary_per_head": 60000.0,
            "customer_churn_pct": 8.0,
            "pricing_change_pct": 0.0,
            "tax_rate_pct": 0.0,
            "capex_monthly": 2000.0,
            "loan_repayment_monthly": 0.0,
            "seasonal_dip_months": [],
        },
    },
]


def get_templates() -> list[ScenarioTemplate]:
    """Return all industry templates."""
    return [ScenarioTemplate(**t) for t in INDUSTRY_TEMPLATES]


def get_template(template_id: str) -> ScenarioTemplate | None:
    """Return a single template by ID."""
    for t in INDUSTRY_TEMPLATES:
        if t["id"] == template_id:
            return ScenarioTemplate(**t)
    return None


# ── Baseline Financials ─────────────────────────────────────────────

async def _get_baseline_financials(db: AsyncSession, ws_id: uuid.UUID, months: int = 6):
    """Get median monthly income/expenses and estimated current cash.

    Uses per-month medians instead of all-time means to avoid distortion
    from outlier months (e.g. one-time funding events, large one-off payments).
    """
    from sqlalchemy import extract, cast, String, literal_column

    # Group transactions by calendar month and type to get monthly totals
    month_label = func.to_char(Transaction.date, literal_column("'YYYY-MM'"))
    result = await db.execute(
        select(
            month_label.label("month"),
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
        ).where(
            Transaction.workspace_id == ws_id
        ).group_by(
            month_label, Transaction.type
        ).order_by(month_label)
    )
    rows = list(result)

    # Build per-month income/expense lists
    monthly_income: list[float] = []
    monthly_expense: list[float] = []
    month_data: dict[str, dict[str, float]] = {}
    for row in rows:
        m, t, total = row[0], row[1], float(row[2] or 0)
        if m not in month_data:
            month_data[m] = {"income": 0.0, "expense": 0.0}
        key = t if isinstance(t, str) else t.value
        month_data[m][key] = total

    for m in sorted(month_data.keys()):
        monthly_income.append(month_data[m].get("income", 0.0))
        monthly_expense.append(month_data[m].get("expense", 0.0))

    if not monthly_income:
        logger.warning("No transaction data for workspace %s — MC will produce zero results", ws_id)
        return 0.0, 0.0, 0.0

    # Use median to resist outlier distortion (e.g. one-time ₹5cr funding month)
    def median(vals: list[float]) -> float:
        s = sorted(vals)
        n = len(s)
        if n == 0:
            return 0.0
        mid = n // 2
        return (s[mid] + s[mid - 1]) / 2 if n % 2 == 0 else s[mid]

    avg_income = median(monthly_income)
    avg_expense = median(monthly_expense)

    # Current cash: use recent 3-month average net as a proxy.
    # Floor at zero — negative starting point should only come from explicit user input.
    recent_inc = monthly_income[-3:] if len(monthly_income) >= 3 else monthly_income
    recent_exp = monthly_expense[-3:] if len(monthly_expense) >= 3 else monthly_expense
    recent_net = sum(recent_inc) - sum(recent_exp)
    current_cash = max(recent_net, 0)

    logger.info(
        "MC baseline ws=%s: median_income=%.0f  median_expense=%.0f  net=%.0f  "
        "recent_3mo_net=%.0f  starting_cash=%.0f  months_data=%d",
        ws_id, avg_income, avg_expense, avg_income - avg_expense,
        recent_net, current_cash, len(monthly_income),
    )
    return avg_income, avg_expense, current_cash


# ── Projection Engine (Extended) ──────────────────────────────────

def _project_scenario(avg_income: float, avg_expense: float, current_cash: float, assumptions: dict, months: int = 12):
    """Project cash flow for N months with full assumption set."""
    a = assumptions
    monthly_points = []
    cumulative = current_cash

    # Pre-compute headcount cost impact
    headcount_cost = a.get("headcount_change", 0) * a.get("avg_salary_per_head", 0) / 12  # annual → monthly

    for m in range(1, months + 1):
        # Base income with growth
        inc = avg_income * (1 + a.get("revenue_growth_pct", 0) / 100) + a.get("new_monthly_revenue", 0)

        # Apply pricing change
        inc *= (1 + a.get("pricing_change_pct", 0) / 100)

        # Apply churn reduction
        churn_factor = 1 - a.get("customer_churn_pct", 0) / 100
        inc *= max(churn_factor, 0)

        # Seasonal dip
        seasonal_months = a.get("seasonal_dip_months", [])
        if m in seasonal_months:
            inc *= 0.7  # 30% dip in seasonal months

        # Base expenses with change
        exp = avg_expense * (1 + a.get("expense_change_pct", 0) / 100) - a.get("removed_monthly_expense", 0)

        # Add headcount cost
        exp += headcount_cost

        # Add capex & loan
        exp += a.get("capex_monthly", 0)
        exp += a.get("loan_repayment_monthly", 0)

        # One-time items (month 1 only)
        if m == 1:
            inc += a.get("one_time_income", 0)
            exp += a.get("one_time_expense", 0)

        # Apply tax on net positive income
        net_before_tax = inc - exp
        tax = 0.0
        tax_rate = a.get("tax_rate_pct", 0)
        if net_before_tax > 0 and tax_rate > 0:
            tax = net_before_tax * (tax_rate / 100)

        net = net_before_tax - tax
        cumulative += net
        monthly_points.append({
            "month": m, "projected_income": round(inc, 2),
            "projected_expenses": round(exp, 2), "tax": round(tax, 2),
            "net_cash_flow": round(net, 2),
            "cumulative_cash": round(cumulative, 2),
        })
    return monthly_points


# ── Scenario CRUD ──────────────────────────────────────────────────

async def list_scenarios(db: AsyncSession, ws_id: uuid.UUID) -> list[Scenario]:
    return list((await db.execute(
        select(Scenario).where(Scenario.workspace_id == ws_id).order_by(Scenario.created_at.desc())
    )).scalars())


async def get_scenario(db: AsyncSession, ws_id: uuid.UUID, scen_id: uuid.UUID) -> Scenario | None:
    return (await db.execute(select(Scenario).where(
        and_(Scenario.id == scen_id, Scenario.workspace_id == ws_id)))).scalar_one_or_none()


async def create_scenario(db: AsyncSession, ws_id: uuid.UUID, user_id: uuid.UUID, data: ScenarioCreate) -> Scenario:
    # Check cap
    count = (await db.execute(select(func.count(Scenario.id)).where(Scenario.workspace_id == ws_id))).scalar()
    if count >= MAX_SCENARIOS:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_SCENARIOS} scenarios per workspace")
    avg_inc, avg_exp, cash = await _get_baseline_financials(db, ws_id)
    assumptions = data.assumptions.model_dump()
    result_data = _project_scenario(avg_inc, avg_exp, cash, assumptions)
    scen = Scenario(
        workspace_id=ws_id, user_id=user_id, name=data.name,
        description=data.description, assumptions_json=assumptions,
        result_json={"monthly": result_data}, is_baseline=data.is_baseline,
        computed_at=datetime.now(timezone.utc),
    )
    db.add(scen); await db.flush(); await db.refresh(scen); return scen


async def update_scenario(db: AsyncSession, ws_id: uuid.UUID, scen: Scenario, data: ScenarioUpdate) -> Scenario:
    if data.name is not None: scen.name = data.name
    if data.description is not None: scen.description = data.description
    if data.assumptions is not None:
        avg_inc, avg_exp, cash = await _get_baseline_financials(db, ws_id)
        assumptions = data.assumptions.model_dump()
        scen.assumptions_json = assumptions
        scen.result_json = {"monthly": _project_scenario(avg_inc, avg_exp, cash, assumptions)}
        scen.computed_at = datetime.now(timezone.utc)
    await db.flush(); await db.refresh(scen); return scen


async def delete_scenario(db: AsyncSession, scen: Scenario) -> None:
    await db.delete(scen); await db.flush()


# ── Comparison ─────────────────────────────────────────────────────

async def compare_scenarios(db: AsyncSession, ws_id: uuid.UUID, scenario_ids: list[uuid.UUID]) -> ScenarioComparisonResponse:
    scenarios = []
    for sid in scenario_ids:
        s = await get_scenario(db, ws_id, sid)
        if s: scenarios.append(s)
    comparison = []
    if scenarios:
        max_months = max(len(s.result_json.get("monthly", [])) for s in scenarios if s.result_json)
        for m in range(max_months):
            point = {"month": m + 1}
            for s in scenarios:
                monthly = s.result_json.get("monthly", []) if s.result_json else []
                if m < len(monthly):
                    point[f"{s.name}_cash"] = monthly[m]["cumulative_cash"]
                    point[f"{s.name}_net"] = monthly[m]["net_cash_flow"]
            comparison.append(point)
    return ScenarioComparisonResponse(
        scenarios=[ScenarioOut.model_validate(s) for s in scenarios],
        comparison_data=comparison,
    )


# ── Sensitivity Analysis ──────────────────────────────────────────

async def run_sensitivity(db: AsyncSession, ws_id: uuid.UUID, scen_id: uuid.UUID, req: SensitivityRequest) -> SensitivityResponse:
    avg_inc, avg_exp, cash = await _get_baseline_financials(db, ws_id)
    scen = await get_scenario(db, ws_id, scen_id)
    base_assumptions = dict(scen.assumptions_json) if scen and scen.assumptions_json else {}
    step_size = (req.range_max - req.range_min) / max(req.steps - 1, 1)
    data_points = []
    for i in range(req.steps):
        val = req.range_min + i * step_size
        assumptions = {**base_assumptions, req.variable_name: val}
        projection = _project_scenario(avg_inc, avg_exp, cash, assumptions)
        final = projection[-1] if projection else {}
        runway = 0
        for p in projection:
            if p["cumulative_cash"] > 0: runway += 1
            else: break
        data_points.append({
            "value": round(val, 2), "runway_months": runway,
            "final_cash": final.get("cumulative_cash", 0),
            "net_cash_flow": final.get("net_cash_flow", 0),
        })
    return SensitivityResponse(variable_name=req.variable_name, data_points=data_points)


# ── Monte Carlo ───────────────────────────────────────────────────

async def run_monte_carlo(db: AsyncSession, ws_id: uuid.UUID, req: MonteCarloRequest) -> MonteCarloResponse:
    avg_inc, avg_exp, cash = await _get_baseline_financials(db, ws_id)
    # Use configurable volatility from request
    rev_std = req.revenue_std
    exp_std = req.expense_std
    results = []
    for _ in range(req.num_simulations):
        cumulative = cash
        runway = 0
        cash_ran_out = False
        for m in range(req.months_ahead):
            # Independent per-month randomization for realistic simulation
            month_inc = avg_inc * max(random.gauss(1.0, rev_std), 0)
            month_exp = avg_exp * max(random.gauss(1.0, exp_std), 0)
            cumulative += month_inc - month_exp
            # Runway = consecutive months from start with positive cash
            if not cash_ran_out and cumulative > 0:
                runway += 1
            else:
                cash_ran_out = True
        results.append({"runway": runway, "final_cash": round(cumulative, 2)})
    runways = sorted([r["runway"] for r in results])
    cashes = sorted([r["final_cash"] for r in results])
    n = len(results)
    return MonteCarloResponse(
        num_simulations=req.num_simulations, months_ahead=req.months_ahead,
        p10_runway=runways[int(n * 0.1)], p50_runway=runways[int(n * 0.5)],
        p90_runway=runways[int(n * 0.9)],
        p10_cash=cashes[int(n * 0.1)], p50_cash=cashes[int(n * 0.5)],
        p90_cash=cashes[int(n * 0.9)],
        distribution=[{"percentile": p, "runway": runways[int(n * p / 100)], "cash": cashes[int(n * p / 100)]}
                       for p in range(10, 100, 10)],
        baseline_monthly_income=round(avg_inc, 2),
        baseline_monthly_expense=round(avg_exp, 2),
        starting_cash=round(cash, 2),
    )


# ── Scenario Sharing ──────────────────────────────────────────────

async def share_scenario(
    db: AsyncSession, scenario_id: uuid.UUID, shared_by_user_id: uuid.UUID, data: ScenarioShareCreate
) -> ScenarioShare:
    share = ScenarioShare(
        scenario_id=scenario_id,
        shared_by_user_id=shared_by_user_id,
        shared_with_user_id=data.shared_with_user_id,
        permission=data.permission,
    )
    db.add(share)
    await db.flush()
    await db.refresh(share)
    return share


async def list_shared_with_me(db: AsyncSession, user_id: uuid.UUID) -> list[ScenarioShare]:
    result = await db.execute(
        select(ScenarioShare).where(ScenarioShare.shared_with_user_id == user_id)
    )
    return list(result.scalars())


async def list_shares_for_scenario(db: AsyncSession, scenario_id: uuid.UUID) -> list[ScenarioShare]:
    result = await db.execute(
        select(ScenarioShare).where(ScenarioShare.scenario_id == scenario_id)
    )
    return list(result.scalars())


async def revoke_share(db: AsyncSession, share_id: uuid.UUID) -> None:
    share = (await db.execute(
        select(ScenarioShare).where(ScenarioShare.id == share_id)
    )).scalar_one_or_none()
    if share:
        await db.delete(share)
        await db.flush()
