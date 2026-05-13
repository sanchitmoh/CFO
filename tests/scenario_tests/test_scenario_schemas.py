#!/usr/bin/env python3
"""Test scenario schemas and data validation."""
import sys
sys.path.insert(0, 'backend')

from schemas import (
    ScenarioCreate,
    ScenarioUpdate,
    ScenarioAssumptions,
    MonteCarloRequest,
    SensitivityRequest,
)
from pydantic import ValidationError

print("="*60)
print("SCENARIO SCHEMA VALIDATION TESTS")
print("="*60)

# Test 1: Valid ScenarioAssumptions
print("\n✅ TEST 1: Valid Scenario Assumptions")
try:
    assumptions = ScenarioAssumptions(
        revenue_growth_pct=10.0,
        expense_change_pct=5.0,
        new_monthly_revenue=0.0,
        removed_monthly_expense=0.0,
        one_time_income=0.0,
        one_time_expense=0.0,
        headcount_change=2,
        avg_salary_per_head=60000.0,
        customer_churn_pct=3.0,
        pricing_change_pct=0.0,
        tax_rate_pct=25.0,
        capex_monthly=5000.0,
        loan_repayment_monthly=0.0,
        seasonal_dip_months=[],
    )
    print(f"   ✅ Valid assumptions created")
    print(f"   Revenue Growth: {assumptions.revenue_growth_pct}%")
    print(f"   Headcount Change: {assumptions.headcount_change}")
except ValidationError as e:
    print(f"   ❌ Validation error: {e}")

# Test 2: Valid ScenarioCreate
print("\n✅ TEST 2: Valid Scenario Creation Request")
try:
    scenario_data = ScenarioCreate(
        name="Test Scenario",
        description="Testing scenario creation",
        assumptions=ScenarioAssumptions(
            revenue_growth_pct=15.0,
            expense_change_pct=10.0,
            headcount_change=5,
            avg_salary_per_head=80000.0,
            customer_churn_pct=3.0,
            tax_rate_pct=25.0,
        )
    )
    print(f"   ✅ Valid scenario create request")
    print(f"   Name: {scenario_data.name}")
    print(f"   Revenue Growth: {scenario_data.assumptions.revenue_growth_pct}%")
except ValidationError as e:
    print(f"   ❌ Validation error: {e}")

# Test 3: Invalid data (negative headcount beyond limit)
print("\n✅ TEST 3: Invalid Headcount (Edge Case)")
try:
    scenario_data = ScenarioCreate(
        name="Invalid Scenario",
        description="Testing validation",
        assumptions=ScenarioAssumptions(
            revenue_growth_pct=10.0,
            headcount_change=-100,  # Too negative
        )
    )
    print(f"   ⚠️  Validation passed (may need stricter validation)")
except ValidationError as e:
    print(f"   ✅ Validation correctly rejected invalid data")
    print(f"   Error: {str(e)[:100]}")

# Test 4: Valid MonteCarloRequest
print("\n✅ TEST 4: Valid Monte Carlo Request")
try:
    mc_request = MonteCarloRequest(
        num_simulations=1000,
        months_ahead=12,
        revenue_std=0.10,
        expense_std=0.08
    )
    print(f"   ✅ Valid Monte Carlo request")
    print(f"   Simulations: {mc_request.num_simulations}")
    print(f"   Months Ahead: {mc_request.months_ahead}")
    print(f"   Revenue Std: {mc_request.revenue_std}")
except ValidationError as e:
    print(f"   ❌ Validation error: {e}")

# Test 5: Valid SensitivityRequest
print("\n✅ TEST 5: Valid Sensitivity Analysis Request")
try:
    sens_request = SensitivityRequest(
        variable_name="revenue_growth_pct",
        range_min=5.0,
        range_max=20.0,
        steps=10
    )
    print(f"   ✅ Valid sensitivity request")
    print(f"   Variable: {sens_request.variable_name}")
    print(f"   Range: {sens_request.range_min} to {sens_request.range_max}")
    print(f"   Steps: {sens_request.steps}")
except ValidationError as e:
    print(f"   ❌ Validation error: {e}")

# Test 6: ScenarioUpdate (partial update)
print("\n✅ TEST 6: Valid Scenario Update (Partial)")
try:
    update_data = ScenarioUpdate(
        name="Updated Name",
        # Only updating name, not assumptions
    )
    print(f"   ✅ Valid partial update")
    print(f"   New name: {update_data.name}")
except ValidationError as e:
    print(f"   ❌ Validation error: {e}")

# Test 7: Extreme values
print("\n✅ TEST 7: Extreme Values (Stress Test)")
test_cases = [
    ("Negative growth", {"revenue_growth_pct": -50.0}),
    ("High growth", {"revenue_growth_pct": 100.0}),
    ("Zero values", {"revenue_growth_pct": 0.0, "headcount_change": 0}),
    ("Large headcount", {"headcount_change": 50}),
]

for name, values in test_cases:
    try:
        assumptions = ScenarioAssumptions(**values)
        print(f"   ✅ {name}: Accepted")
    except ValidationError as e:
        print(f"   ❌ {name}: Rejected - {str(e)[:50]}")

# Test 8: Seasonal dip months validation
print("\n✅ TEST 8: Seasonal Dip Months")
test_cases = [
    ("Valid months", [1, 2, 12]),
    ("Empty list", []),
    ("All months", list(range(1, 13))),
]

for name, months in test_cases:
    try:
        assumptions = ScenarioAssumptions(
            revenue_growth_pct=10.0,
            seasonal_dip_months=months
        )
        print(f"   ✅ {name}: {months}")
    except ValidationError as e:
        print(f"   ❌ {name}: Rejected")

print("\n" + "="*60)
print("✅ SCHEMA VALIDATION TESTS COMPLETE")
print("="*60)
