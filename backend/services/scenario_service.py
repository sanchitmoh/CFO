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
from statistics import pstdev

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
RATE_FIELDS = (
    "revenue_growth_pct",
    "expense_change_pct",
    "customer_churn_pct",
    "pricing_change_pct",
    "tax_rate_pct",
)
RATE_MODE_PERCENT = "percent"
RATE_MODE_DECIMAL = "decimal"


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


def _get_rate_input_mode(assumptions: dict) -> str:
    """Support both percent-style inputs (15 = 15%) and decimal inputs (0.15 = 15%)."""
    explicit_mode = assumptions.get("rate_input_mode")
    if explicit_mode in {RATE_MODE_PERCENT, RATE_MODE_DECIMAL}:
        return explicit_mode

    nonzero_rates = []
    for key in RATE_FIELDS:
        value = assumptions.get(key, 0)
        if value in (None, 0):
            continue
        nonzero_rates.append(abs(float(value)))

    if nonzero_rates and all(value <= 1 for value in nonzero_rates):
        return RATE_MODE_DECIMAL

    return RATE_MODE_PERCENT


def _get_rate_ratio(assumptions: dict, key: str, rate_mode: str | None = None) -> float:
    rate_mode = rate_mode or _get_rate_input_mode(assumptions)
    raw_value = float(assumptions.get(key, 0) or 0)
    if raw_value == 0:
        return 0.0
    if rate_mode == RATE_MODE_DECIMAL:
        return raw_value
    return raw_value / 100


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    middle = len(sorted_values) // 2
    if len(sorted_values) % 2 == 0:
        return (sorted_values[middle] + sorted_values[middle - 1]) / 2
    return sorted_values[middle]


async def _get_monthly_financial_series(db: AsyncSession, ws_id: uuid.UUID) -> dict[str, list[float] | float]:
    from sqlalchemy import literal_column

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

    month_data: dict[str, dict[str, float]] = {}
    for row in result:
        month, txn_type, total = row[0], row[1], float(row[2] or 0)
        if month not in month_data:
            month_data[month] = {"income": 0.0, "expense": 0.0}
        key = txn_type if isinstance(txn_type, str) else txn_type.value
        month_data[month][key] = total

    monthly_income: list[float] = []
    monthly_expense: list[float] = []
    for month in sorted(month_data):
        monthly_income.append(month_data[month].get("income", 0.0))
        monthly_expense.append(month_data[month].get("expense", 0.0))

    return {
        "income": monthly_income,
        "expense": monthly_expense,
        "starting_cash": sum(monthly_income) - sum(monthly_expense),
    }


def _build_projection_components(avg_income: float, avg_expense: float, assumptions: dict, months: int = 12) -> list[dict]:
    a = assumptions
    rate_mode = _get_rate_input_mode(a)
    revenue_growth = _get_rate_ratio(a, "revenue_growth_pct", rate_mode)
    expense_change = _get_rate_ratio(a, "expense_change_pct", rate_mode)
    pricing_change = _get_rate_ratio(a, "pricing_change_pct", rate_mode)
    churn_rate = _get_rate_ratio(a, "customer_churn_pct", rate_mode)
    tax_rate = _get_rate_ratio(a, "tax_rate_pct", rate_mode)
    headcount_cost = a.get("headcount_change", 0) * a.get("avg_salary_per_head", 0) / 12
    recurring_income = avg_income
    recurring_expense = avg_expense
    seasonal_months = set(a.get("seasonal_dip_months", []))
    components: list[dict] = []

    for month in range(1, months + 1):
        recurring_income = recurring_income * (1 + revenue_growth) + a.get("new_monthly_revenue", 0)
        recurring_income *= (1 + pricing_change)
        recurring_income *= max(1 - churn_rate, 0)
        projected_income = recurring_income
        if month in seasonal_months:
            projected_income *= 0.7

        recurring_expense = recurring_expense * (1 + expense_change) - a.get("removed_monthly_expense", 0)
        projected_expense = recurring_expense + headcount_cost
        projected_expense += a.get("capex_monthly", 0)
        projected_expense += a.get("loan_repayment_monthly", 0)

        components.append({
            "month": month,
            "income": projected_income,
            "expense": projected_expense,
            "one_time_income": a.get("one_time_income", 0) if month == 1 else 0.0,
            "one_time_expense": a.get("one_time_expense", 0) if month == 1 else 0.0,
            "tax_rate": tax_rate,
        })

    return components


def _derive_volatility(values: list[float]) -> float:
    changes = []
    for previous, current in zip(values, values[1:]):
        if previous > 0:
            changes.append((current - previous) / previous)

    if len(changes) >= 2:
        return float(pstdev(changes))

    positive_values = [value for value in values if value > 0]
    if len(positive_values) >= 2:
        average = sum(positive_values) / len(positive_values)
        if average > 0:
            return float(pstdev(positive_values) / average)

    return 0.0


def _percentile_index(length: int, percentile: float) -> int:
    if length <= 1:
        return 0
    return max(0, min(length - 1, int((length - 1) * percentile)))


def _simulate_monte_carlo(
    components: list[dict],
    starting_cash: float,
    num_simulations: int,
    revenue_std: float,
    expense_std: float,
) -> list[dict]:
    results = []
    for _ in range(num_simulations):
        cumulative = starting_cash
        runway = 0
        cash_ran_out = False

        for component in components:
            income_noise = max(random.gauss(1.0, revenue_std), 0)
            expense_noise = max(random.gauss(1.0, expense_std), 0)
            month_income = component["income"] * income_noise + component["one_time_income"]
            month_expense = component["expense"] * expense_noise + component["one_time_expense"]
            net_before_tax = month_income - month_expense
            month_tax = net_before_tax * component["tax_rate"] if net_before_tax > 0 and component["tax_rate"] > 0 else 0.0
            cumulative += net_before_tax - month_tax

            if not cash_ran_out and cumulative > 0:
                runway += 1
            else:
                cash_ran_out = True

        results.append({"runway": runway, "final_cash": round(cumulative, 2)})

    return results


# ── Baseline Financials ─────────────────────────────────────────────

async def _get_baseline_financials(db: AsyncSession, ws_id: uuid.UUID, months: int = 6):
    """Get median monthly income/expenses and estimated current cash.

    Uses per-month medians instead of all-time means to avoid distortion
    from outlier months (e.g. one-time funding events, large one-off payments).
    """
    series = await _get_monthly_financial_series(db, ws_id)
    monthly_income = list(series["income"])
    monthly_expense = list(series["expense"])

    if not monthly_income:
        logger.warning("No transaction data for workspace %s — MC will produce zero results", ws_id)
        return 0.0, 0.0, 0.0

    # Use median to resist outlier distortion (e.g. one-time ₹5cr funding month)
    avg_income = _median(monthly_income)
    avg_expense = _median(monthly_expense)

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
    monthly_points = []
    cumulative = current_cash
    components = _build_projection_components(avg_income, avg_expense, assumptions, months)

    for component in components:
        inc = component["income"] + component["one_time_income"]
        exp = component["expense"] + component["one_time_expense"]
        net_before_tax = inc - exp
        tax = 0.0
        if net_before_tax > 0 and component["tax_rate"] > 0:
            tax = net_before_tax * component["tax_rate"]

        net = net_before_tax - tax
        cumulative += net
        monthly_points.append({
            "month": component["month"],
            "projected_income": round(inc, 2),
            "projected_expenses": round(exp, 2),
            "tax": round(tax, 2),
            "net_cash_flow": round(net, 2),
            "cumulative_cash": round(cumulative, 2),
        })
    return monthly_points

    # Pre-compute headcount cost impact
    headcount_cost = a.get("headcount_change", 0) * a.get("avg_salary_per_head", 0) / 12  # annual → monthly

    for component in components:
        inc = component["income"] + component["one_time_income"]
        exp = component["expense"] + component["one_time_expense"]
        net_before_tax = inc - exp
        tax = 0.0
        if net_before_tax > 0 and tax_rate > 0:
            tax = net_before_tax * tax_rate

        net = net_before_tax - tax
        cumulative += net
        monthly_points.append({
            "month": m, "projected_income": round(inc, 2),
            "projected_expenses": round(exp, 2), "tax": round(tax, 2),
            "net_cash_flow": round(net, 2),
            "cumulative_cash": round(cumulative, 2),
        })
    return monthly_points


def _refresh_scenario_projection(scenario: Scenario, avg_income: float, avg_expense: float, current_cash: float) -> None:
    if not scenario.assumptions_json:
        return

    scenario.result_json = {
        "monthly": _project_scenario(avg_income, avg_expense, current_cash, dict(scenario.assumptions_json))
    }
    scenario.computed_at = datetime.now(timezone.utc)


# ── Scenario CRUD ──────────────────────────────────────────────────

async def list_scenarios(db: AsyncSession, ws_id: uuid.UUID) -> list[Scenario]:
    scenarios = list((await db.execute(
        select(Scenario).where(Scenario.workspace_id == ws_id).order_by(Scenario.created_at.desc())
    )).scalars())
    if scenarios:
        avg_inc, avg_exp, cash = await _get_baseline_financials(db, ws_id)
        for scenario in scenarios:
            _refresh_scenario_projection(scenario, avg_inc, avg_exp, cash)
    return scenarios


async def get_scenario(db: AsyncSession, ws_id: uuid.UUID, scen_id: uuid.UUID) -> Scenario | None:
    scenario = (await db.execute(select(Scenario).where(
        and_(Scenario.id == scen_id, Scenario.workspace_id == ws_id)))).scalar_one_or_none()
    if scenario:
        avg_inc, avg_exp, cash = await _get_baseline_financials(db, ws_id)
        _refresh_scenario_projection(scenario, avg_inc, avg_exp, cash)
    return scenario


async def create_scenario(db: AsyncSession, ws_id: uuid.UUID, user_id: uuid.UUID, data: ScenarioCreate) -> Scenario:
    # Check cap
    count = (await db.execute(select(func.count(Scenario.id)).where(Scenario.workspace_id == ws_id))).scalar()
    if count >= MAX_SCENARIOS:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_SCENARIOS} scenarios per workspace")
    avg_inc, avg_exp, cash = await _get_baseline_financials(db, ws_id)
    assumptions = data.assumptions.model_dump()
    scen = Scenario(
        workspace_id=ws_id, user_id=user_id, name=data.name,
        description=data.description, assumptions_json=assumptions,
        is_baseline=data.is_baseline,
        computed_at=datetime.now(timezone.utc),
    )
    _refresh_scenario_projection(scen, avg_inc, avg_exp, cash)
    db.add(scen); await db.flush(); await db.refresh(scen); return scen


async def update_scenario(db: AsyncSession, ws_id: uuid.UUID, scen: Scenario, data: ScenarioUpdate) -> Scenario:
    if data.name is not None: scen.name = data.name
    if data.description is not None: scen.description = data.description
    if data.assumptions is not None:
        avg_inc, avg_exp, cash = await _get_baseline_financials(db, ws_id)
        assumptions = data.assumptions.model_dump()
        scen.assumptions_json = assumptions
        _refresh_scenario_projection(scen, avg_inc, avg_exp, cash)
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
    from fastapi import HTTPException

    series = await _get_monthly_financial_series(db, ws_id)
    monthly_income = list(series["income"])
    monthly_expense = list(series["expense"])
    starting_cash = float(series["starting_cash"] or 0)
    avg_inc = _median(monthly_income)
    avg_exp = _median(monthly_expense)

    assumptions: dict = {}
    if req.scenario_id is not None:
        scenario = await get_scenario(db, ws_id, req.scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        assumptions = dict(scenario.assumptions_json or {})

    rev_std = req.revenue_std if req.revenue_std is not None else _derive_volatility(monthly_income)
    exp_std = req.expense_std if req.expense_std is not None else _derive_volatility(monthly_expense)
    components = _build_projection_components(avg_inc, avg_exp, assumptions, req.months_ahead)
    results = _simulate_monte_carlo(components, starting_cash, req.num_simulations, rev_std, exp_std)
    runways = sorted(result["runway"] for result in results)
    cashes = sorted(result["final_cash"] for result in results)
    ordered_distribution = sorted(results, key=lambda result: (result["runway"], result["final_cash"]))
    n = len(results)
    p10_index = _percentile_index(n, 0.10)
    p50_index = _percentile_index(n, 0.50)
    p90_index = _percentile_index(n, 0.90)

    return MonteCarloResponse(
        num_simulations=req.num_simulations,
        months_ahead=req.months_ahead,
        p10_runway=runways[p10_index],
        p50_runway=runways[p50_index],
        p90_runway=runways[p90_index],
        p10_cash=cashes[p10_index],
        p50_cash=cashes[p50_index],
        p90_cash=cashes[p90_index],
        distribution=[
            {
                "percentile": percentile,
                "runway": ordered_distribution[_percentile_index(n, percentile / 100)]["runway"],
                "cash": ordered_distribution[_percentile_index(n, percentile / 100)]["final_cash"],
            }
            for percentile in range(10, 100, 10)
        ],
        baseline_monthly_income=round(avg_inc, 2),
        baseline_monthly_expense=round(avg_exp, 2),
        starting_cash=round(starting_cash, 2),
        revenue_std_used=round(rev_std, 6),
        expense_std_used=round(exp_std, 6),
        scenario_id=req.scenario_id,
    )

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
