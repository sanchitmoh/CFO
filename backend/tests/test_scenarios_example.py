"""
AI CFO — Scenario Testing Examples
Complete test suite demonstrating scenario creation, testing, and analysis.
"""
import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from services.scenario_service import (
    create_scenario,
    get_scenario,
    list_scenarios,
    update_scenario,
    delete_scenario,
    compare_scenarios,
    run_monte_carlo,
    run_sensitivity_analysis,
    get_templates,
    get_template,
    share_scenario,
    list_shared_with_me,
)
from schemas import (
    ScenarioCreate,
    ScenarioUpdate,
    MonteCarloRequest,
    SensitivityRequest,
    ScenarioShareCreate,
)


# ═══════════════════════════════════════════════════════════════════
# BASIC CRUD TESTS
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_basic_scenario(db: AsyncSession):
    """Test creating a basic scenario with minimal assumptions."""
    
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    data = ScenarioCreate(
        name="Basic Growth Scenario",
        description="10% revenue growth, 5% expense increase",
        assumptions={
            "revenue_growth_pct": 10.0,
            "expense_change_pct": 5.0,
            "headcount_change": 0,
            "avg_salary_per_head": 0.0,
            "customer_churn_pct": 0.0,
            "pricing_change_pct": 0.0,
            "tax_rate_pct": 25.0,
            "capex_monthly": 0.0,
            "loan_repayment_monthly": 0.0,
            "seasonal_dip_months": [],
        }
    )
    
    scenario = await create_scenario(db, workspace_id, user_id, data)
    await db.commit()
    
    assert scenario.name == "Basic Growth Scenario"
    assert scenario.workspace_id == workspace_id
    assert scenario.created_by == user_id
    assert scenario.assumptions["revenue_growth_pct"] == 10.0
    assert scenario.assumptions["expense_change_pct"] == 5.0
    
    print(f"✅ Created scenario: {scenario.id}")
    print(f"   Name: {scenario.name}")
    print(f"   Revenue Growth: {scenario.assumptions['revenue_growth_pct']}%")
    print(f"   Expense Change: {scenario.assumptions['expense_change_pct']}%")


@pytest.mark.asyncio
async def test_create_complex_scenario(db: AsyncSession):
    """Test creating a complex scenario with all assumptions."""
    
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    data = ScenarioCreate(
        name="SaaS Growth Plan Q3 2026",
        description="Aggressive growth: 15% revenue, 5 new hires, 3% churn",
        assumptions={
            "revenue_growth_pct": 15.0,
            "expense_change_pct": 10.0,
            "new_monthly_revenue": 50000.0,
            "removed_monthly_expense": 5000.0,
            "one_time_income": 100000.0,
            "one_time_expense": 25000.0,
            "headcount_change": 5,
            "avg_salary_per_head": 80000.0,
            "customer_churn_pct": 3.0,
            "pricing_change_pct": 5.0,
            "tax_rate_pct": 25.0,
            "capex_monthly": 10000.0,
            "loan_repayment_monthly": 5000.0,
            "seasonal_dip_months": [1, 7],
        }
    )
    
    scenario = await create_scenario(db, workspace_id, user_id, data)
    await db.commit()
    
    assert scenario.name == "SaaS Growth Plan Q3 2026"
    assert scenario.assumptions["headcount_change"] == 5
    assert scenario.assumptions["avg_salary_per_head"] == 80000.0
    assert scenario.assumptions["one_time_income"] == 100000.0
    assert len(scenario.assumptions["seasonal_dip_months"]) == 2
    
    print(f"✅ Created complex scenario: {scenario.id}")
    print(f"   Headcount Change: +{scenario.assumptions['headcount_change']}")
    print(f"   Avg Salary: ${scenario.assumptions['avg_salary_per_head']:,.0f}")
    print(f"   One-time Income: ${scenario.assumptions['one_time_income']:,.0f}")


@pytest.mark.asyncio
async def test_get_scenario(db: AsyncSession):
    """Test retrieving a scenario by ID."""
    
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # Create scenario
    data = ScenarioCreate(
        name="Test Scenario",
        description="For retrieval test",
        assumptions={"revenue_growth_pct": 10.0}
    )
    created = await create_scenario(db, workspace_id, user_id, data)
    await db.commit()
    
    # Retrieve scenario
    retrieved = await get_scenario(db, workspace_id, created.id)
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.name == "Test Scenario"
    
    print(f"✅ Retrieved scenario: {retrieved.id}")


@pytest.mark.asyncio
async def test_list_scenarios(db: AsyncSession):
    """Test listing all scenarios in a workspace."""
    
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # Create 3 scenarios
    for i in range(3):
        data = ScenarioCreate(
            name=f"Scenario {i+1}",
            description=f"Test scenario {i+1}",
            assumptions={"revenue_growth_pct": float(i * 5)}
        )
        await create_scenario(db, workspace_id, user_id, data)
    
    await db.commit()
    
    # List scenarios
    scenarios = await list_scenarios(db, workspace_id)
    
    assert len(scenarios) >= 3
    
    print(f"✅ Listed {len(scenarios)} scenarios")
    for s in scenarios:
        print(f"   - {s.name}: {s.assumptions['revenue_growth_pct']}% growth")


@pytest.mark.asyncio
async def test_update_scenario(db: AsyncSession):
    """Test updating a scenario."""
    
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # Create scenario
    data = ScenarioCreate(
        name="Original Name",
        description="Original description",
        assumptions={"revenue_growth_pct": 10.0}
    )
    scenario = await create_scenario(db, workspace_id, user_id, data)
    await db.commit()
    
    # Update scenario
    update_data = ScenarioUpdate(
        name="Updated Name",
        description="Updated description",
        assumptions={"revenue_growth_pct": 15.0}
    )
    updated = await update_scenario(db, workspace_id, scenario.id, update_data)
    await db.commit()
    
    assert updated.name == "Updated Name"
    assert updated.description == "Updated description"
    assert updated.assumptions["revenue_growth_pct"] == 15.0
    
    print(f"✅ Updated scenario: {updated.id}")
    print(f"   Old: Original Name (10% growth)")
    print(f"   New: {updated.name} ({updated.assumptions['revenue_growth_pct']}% growth)")


@pytest.mark.asyncio
async def test_delete_scenario(db: AsyncSession):
    """Test deleting a scenario."""
    
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # Create scenario
    data = ScenarioCreate(
        name="To Be Deleted",
        description="This will be deleted",
        assumptions={"revenue_growth_pct": 10.0}
    )
    scenario = await create_scenario(db, workspace_id, user_id, data)
    await db.commit()
    
    scenario_id = scenario.id
    
    # Delete scenario
    await delete_scenario(db, workspace_id, scenario_id)
    await db.commit()
    
    # Verify deletion
    deleted = await get_scenario(db, workspace_id, scenario_id)
    assert deleted is None
    
    print(f"✅ Deleted scenario: {scenario_id}")


# ═══════════════════════════════════════════════════════════════════
# COMPARISON TESTS
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_compare_two_scenarios(db: AsyncSession):
    """Test comparing two scenarios (best case vs worst case)."""
    
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # Create best case scenario
    best_case = ScenarioCreate(
        name="Best Case",
        description="Optimistic: 20% growth, low churn",
        assumptions={
            "revenue_growth_pct": 20.0,
            "expense_change_pct": 5.0,
            "customer_churn_pct": 1.0,
        }
    )
    best = await create_scenario(db, workspace_id, user_id, best_case)
    
    # Create worst case scenario
    worst_case = ScenarioCreate(
        name="Worst Case",
        description="Pessimistic: 0% growth, high churn",
        assumptions={
            "revenue_growth_pct": 0.0,
            "expense_change_pct": 15.0,
            "customer_churn_pct": 10.0,
        }
    )
    worst = await create_scenario(db, workspace_id, user_id, worst_case)
    
    await db.commit()
    
    # Compare scenarios
    comparison = await compare_scenarios(db, workspace_id, [best.id, worst.id])
    
    assert len(comparison["scenarios"]) == 2
    assert "comparison_metrics" in comparison
    
    print(f"✅ Compared 2 scenarios:")
    print(f"   Best Case: {best.assumptions['revenue_growth_pct']}% growth")
    print(f"   Worst Case: {worst.assumptions['revenue_growth_pct']}% growth")


@pytest.mark.asyncio
async def test_compare_multiple_scenarios(db: AsyncSession):
    """Test comparing multiple scenarios (conservative, moderate, aggressive)."""
    
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    scenarios = []
    
    # Conservative
    conservative = ScenarioCreate(
        name="Conservative",
        description="5% growth, minimal hiring",
        assumptions={
            "revenue_growth_pct": 5.0,
            "expense_change_pct": 3.0,
            "headcount_change": 1,
        }
    )
    scenarios.append(await create_scenario(db, workspace_id, user_id, conservative))
    
    # Moderate
    moderate = ScenarioCreate(
        name="Moderate",
        description="10% growth, steady hiring",
        assumptions={
            "revenue_growth_pct": 10.0,
            "expense_change_pct": 7.0,
            "headcount_change": 3,
        }
    )
    scenarios.append(await create_scenario(db, workspace_id, user_id, moderate))
    
    # Aggressive
    aggressive = ScenarioCreate(
        name="Aggressive",
        description="20% growth, rapid hiring",
        assumptions={
            "revenue_growth_pct": 20.0,
            "expense_change_pct": 15.0,
            "headcount_change": 8,
        }
    )
    scenarios.append(await create_scenario(db, workspace_id, user_id, aggressive))
    
    await db.commit()
    
    # Compare all scenarios
    scenario_ids = [s.id for s in scenarios]
    comparison = await compare_scenarios(db, workspace_id, scenario_ids)
    
    assert len(comparison["scenarios"]) == 3
    
    print(f"✅ Compared 3 scenarios:")
    for s in scenarios:
        print(f"   {s.name}: {s.assumptions['revenue_growth_pct']}% growth, "
              f"+{s.assumptions['headcount_change']} headcount")


# ═══════════════════════════════════════════════════════════════════
# MONTE CARLO SIMULATION TESTS
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_monte_carlo_single_variable(db: AsyncSession):
    """Test Monte Carlo simulation with single variable."""
    
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # Create scenario
    data = ScenarioCreate(
        name="Monte Carlo Test",
        description="Testing Monte Carlo with revenue growth",
        assumptions={"revenue_growth_pct": 10.0}
    )
    scenario = await create_scenario(db, workspace_id, user_id, data)
    await db.commit()
    
    # Run Monte Carlo
    request = MonteCarloRequest(
        scenario_id=scenario.id,
        num_simulations=1000,
        variables={
            "revenue_growth_pct": {
                "min": 5.0,
                "max": 15.0,
                "distribution": "normal"
            }
        }
    )
    
    result = await run_monte_carlo(db, workspace_id, request)
    
    assert result["num_simulations"] == 1000
    assert "percentiles" in result
    assert "mean_outcome" in result
    assert "std_dev" in result
    
    print(f"✅ Monte Carlo simulation complete:")
    print(f"   Simulations: {result['num_simulations']}")
    print(f"   Mean Outcome: {result['mean_outcome']}")
    print(f"   Std Dev: {result['std_dev']}")
    print(f"   P10: {result['percentiles']['p10']}")
    print(f"   P50: {result['percentiles']['p50']}")
    print(f"   P90: {result['percentiles']['p90']}")


@pytest.mark.asyncio
async def test_monte_carlo_multiple_variables(db: AsyncSession):
    """Test Monte Carlo simulation with multiple variables."""
    
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # Create scenario
    data = ScenarioCreate(
        name="Multi-Variable Monte Carlo",
        description="Testing with revenue and expenses",
        assumptions={
            "revenue_growth_pct": 10.0,
            "expense_change_pct": 5.0,
            "customer_churn_pct": 3.0,
        }
    )
    scenario = await create_scenario(db, workspace_id, user_id, data)
    await db.commit()
    
    # Run Monte Carlo with 3 variables
    request = MonteCarloRequest(
        scenario_id=scenario.id,
        num_simulations=1000,
        variables={
            "revenue_growth_pct": {
                "min": 5.0,
                "max": 20.0,
                "distribution": "normal"
            },
            "expense_change_pct": {
                "min": 0.0,
                "max": 15.0,
                "distribution": "uniform"
            },
            "customer_churn_pct": {
                "min": 1.0,
                "max": 5.0,
                "distribution": "normal"
            }
        }
    )
    
    result = await run_monte_carlo(db, workspace_id, request)
    
    assert result["num_simulations"] == 1000
    assert len(result["variable_impacts"]) == 3
    
    print(f"✅ Multi-variable Monte Carlo complete:")
    print(f"   Variables tested: {len(result['variable_impacts'])}")
    for var, impact in result["variable_impacts"].items():
        print(f"   {var}: {impact}")


# ═══════════════════════════════════════════════════════════════════
# SENSITIVITY ANALYSIS TESTS
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_sensitivity_analysis(db: AsyncSession):
    """Test sensitivity analysis on key variables."""
    
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # Create scenario
    data = ScenarioCreate(
        name="Sensitivity Test",
        description="Testing sensitivity to key variables",
        assumptions={
            "revenue_growth_pct": 10.0,
            "expense_change_pct": 5.0,
            "customer_churn_pct": 3.0,
            "pricing_change_pct": 0.0,
        }
    )
    scenario = await create_scenario(db, workspace_id, user_id, data)
    await db.commit()
    
    # Run sensitivity analysis
    request = SensitivityRequest(
        scenario_id=scenario.id,
        variables=[
            "revenue_growth_pct",
            "expense_change_pct",
            "customer_churn_pct",
            "pricing_change_pct"
        ],
        range_pct=20.0  # ±20% variation
    )
    
    result = await run_sensitivity_analysis(db, workspace_id, request)
    
    assert len(result["variables"]) == 4
    assert "tornado_chart_data" in result
    assert "most_sensitive" in result
    
    print(f"✅ Sensitivity analysis complete:")
    print(f"   Variables tested: {len(result['variables'])}")
    print(f"   Most sensitive: {result['most_sensitive']}")
    for var_result in result["variables"]:
        print(f"   {var_result['variable']}: Impact = {var_result['impact']}")


# ═══════════════════════════════════════════════════════════════════
# TEMPLATE TESTS
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_templates():
    """Test listing all scenario templates."""
    
    templates = get_templates()
    
    assert len(templates) >= 4  # SaaS, Retail, Services, Manufacturing
    
    print(f"✅ Found {len(templates)} templates:")
    for template in templates:
        print(f"   - {template['name']} ({template['industry']})")


@pytest.mark.asyncio
async def test_get_saas_template():
    """Test getting SaaS startup template."""
    
    template = get_template("saas_startup")
    
    assert template is not None
    assert template["name"] == "SaaS Startup"
    assert template["industry"] == "Technology / SaaS"
    assert "assumptions" in template
    assert template["assumptions"]["revenue_growth_pct"] == 15.0
    
    print(f"✅ SaaS Startup template:")
    print(f"   Revenue Growth: {template['assumptions']['revenue_growth_pct']}%")
    print(f"   Headcount Change: +{template['assumptions']['headcount_change']}")
    print(f"   Avg Salary: ${template['assumptions']['avg_salary_per_head']:,.0f}")


@pytest.mark.asyncio
async def test_create_from_template(db: AsyncSession):
    """Test creating a scenario from a template."""
    
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # Get template
    template = get_template("retail_ecommerce")
    assert template is not None
    
    # Create scenario from template
    data = ScenarioCreate(
        name="Q4 Holiday Season",
        description=f"Based on {template['name']} template",
        assumptions=template["assumptions"]
    )
    
    scenario = await create_scenario(db, workspace_id, user_id, data)
    await db.commit()
    
    assert scenario.name == "Q4 Holiday Season"
    assert scenario.assumptions["revenue_growth_pct"] == template["assumptions"]["revenue_growth_pct"]
    assert len(scenario.assumptions["seasonal_dip_months"]) > 0
    
    print(f"✅ Created scenario from template:")
    print(f"   Template: {template['name']}")
    print(f"   Scenario: {scenario.name}")
    print(f"   Seasonal dips: {scenario.assumptions['seasonal_dip_months']}")


# ═══════════════════════════════════════════════════════════════════
# SHARING TESTS
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_share_scenario(db: AsyncSession):
    """Test sharing a scenario with another user."""
    
    workspace_id = str(uuid.uuid4())
    owner_id = str(uuid.uuid4())
    recipient_id = str(uuid.uuid4())
    
    # Create scenario
    data = ScenarioCreate(
        name="Shared Scenario",
        description="This will be shared",
        assumptions={"revenue_growth_pct": 10.0}
    )
    scenario = await create_scenario(db, workspace_id, owner_id, data)
    await db.commit()
    
    # Share scenario
    share_data = ScenarioShareCreate(
        scenario_id=scenario.id,
        shared_with_user_id=recipient_id,
        can_edit=False
    )
    
    share = await share_scenario(db, workspace_id, owner_id, share_data)
    await db.commit()
    
    assert share.scenario_id == scenario.id
    assert share.shared_with_user_id == recipient_id
    assert share.can_edit is False
    
    print(f"✅ Shared scenario:")
    print(f"   Scenario: {scenario.name}")
    print(f"   Shared with: {recipient_id}")
    print(f"   Can edit: {share.can_edit}")


@pytest.mark.asyncio
async def test_list_shared_scenarios(db: AsyncSession):
    """Test listing scenarios shared with a user."""
    
    workspace_id = str(uuid.uuid4())
    owner_id = str(uuid.uuid4())
    recipient_id = str(uuid.uuid4())
    
    # Create and share 2 scenarios
    for i in range(2):
        data = ScenarioCreate(
            name=f"Shared Scenario {i+1}",
            description=f"Scenario {i+1}",
            assumptions={"revenue_growth_pct": float(i * 5)}
        )
        scenario = await create_scenario(db, workspace_id, owner_id, data)
        
        share_data = ScenarioShareCreate(
            scenario_id=scenario.id,
            shared_with_user_id=recipient_id,
            can_edit=(i == 1)  # Second one can be edited
        )
        await share_scenario(db, workspace_id, owner_id, share_data)
    
    await db.commit()
    
    # List shared scenarios
    shared = await list_shared_with_me(db, recipient_id)
    
    assert len(shared) >= 2
    
    print(f"✅ Listed {len(shared)} shared scenarios:")
    for s in shared:
        print(f"   - Scenario {s.scenario_id}: Can edit = {s.can_edit}")


# ═══════════════════════════════════════════════════════════════════
# EDGE CASE TESTS
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_negative_growth_scenario(db: AsyncSession):
    """Test scenario with negative growth (recession)."""
    
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    data = ScenarioCreate(
        name="Recession Scenario",
        description="Negative growth, cost cutting",
        assumptions={
            "revenue_growth_pct": -10.0,
            "expense_change_pct": -15.0,
            "headcount_change": -5,
            "customer_churn_pct": 8.0,
        }
    )
    
    scenario = await create_scenario(db, workspace_id, user_id, data)
    await db.commit()
    
    assert scenario.assumptions["revenue_growth_pct"] == -10.0
    assert scenario.assumptions["headcount_change"] == -5
    
    print(f"✅ Created recession scenario:")
    print(f"   Revenue Growth: {scenario.assumptions['revenue_growth_pct']}%")
    print(f"   Headcount Change: {scenario.assumptions['headcount_change']}")


@pytest.mark.asyncio
async def test_extreme_growth_scenario(db: AsyncSession):
    """Test scenario with extreme growth (viral/hockey stick)."""
    
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    data = ScenarioCreate(
        name="Viral Growth",
        description="100% monthly growth (hockey stick)",
        assumptions={
            "revenue_growth_pct": 100.0,
            "expense_change_pct": 50.0,
            "headcount_change": 20,
            "customer_churn_pct": 1.0,
        }
    )
    
    scenario = await create_scenario(db, workspace_id, user_id, data)
    await db.commit()
    
    assert scenario.assumptions["revenue_growth_pct"] == 100.0
    
    print(f"✅ Created viral growth scenario:")
    print(f"   Revenue Growth: {scenario.assumptions['revenue_growth_pct']}%")
    print(f"   Headcount Change: +{scenario.assumptions['headcount_change']}")


@pytest.mark.asyncio
async def test_zero_change_scenario(db: AsyncSession):
    """Test scenario with no changes (status quo)."""
    
    workspace_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    data = ScenarioCreate(
        name="Status Quo",
        description="No changes, maintain current state",
        assumptions={
            "revenue_growth_pct": 0.0,
            "expense_change_pct": 0.0,
            "headcount_change": 0,
            "customer_churn_pct": 0.0,
            "pricing_change_pct": 0.0,
        }
    )
    
    scenario = await create_scenario(db, workspace_id, user_id, data)
    await db.commit()
    
    assert scenario.assumptions["revenue_growth_pct"] == 0.0
    assert scenario.assumptions["headcount_change"] == 0
    
    print(f"✅ Created status quo scenario:")
    print(f"   All changes: 0%")


if __name__ == "__main__":
    print("Run with: pytest backend/tests/test_scenarios_example.py -v -s")
