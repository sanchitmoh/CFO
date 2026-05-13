#!/usr/bin/env python3
"""
AI CFO — Manual Scenario Testing Script
Interactive script for testing scenario creation and analysis.

Usage:
    python test_scenarios_manual.py
"""
import asyncio
import httpx
import json
from typing import Optional
from datetime import datetime


# Configuration
API_BASE_URL = "http://localhost:8000"
JWT_TOKEN = None  # Set this or pass via command line


class ScenarioTester:
    """Interactive scenario testing client."""
    
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url
        self.token = token
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
    
    async def create_scenario(self, name: str, description: str, assumptions: dict) -> dict:
        """Create a new scenario."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/scenarios",
                headers=self.headers,
                json={
                    "name": name,
                    "description": description,
                    "assumptions": assumptions
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def list_scenarios(self) -> list:
        """List all scenarios."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/scenarios",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_scenario(self, scenario_id: str) -> dict:
        """Get scenario details."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/scenarios/{scenario_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def compare_scenarios(self, scenario_ids: list) -> dict:
        """Compare multiple scenarios."""
        ids_str = ",".join(scenario_ids)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/scenarios/compare?ids={ids_str}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def run_monte_carlo(self, scenario_id: str, num_simulations: int, variables: dict) -> dict:
        """Run Monte Carlo simulation."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/scenarios/monte-carlo",
                headers=self.headers,
                json={
                    "scenario_id": scenario_id,
                    "num_simulations": num_simulations,
                    "variables": variables
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def run_sensitivity(self, scenario_id: str, variables: list, range_pct: float) -> dict:
        """Run sensitivity analysis."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/scenarios/sensitivity",
                headers=self.headers,
                json={
                    "scenario_id": scenario_id,
                    "variables": variables,
                    "range_pct": range_pct
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def list_templates(self) -> list:
        """List scenario templates."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/scenarios/templates",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_template(self, template_id: str) -> dict:
        """Get template details."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/scenarios/templates/{template_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()


# ═══════════════════════════════════════════════════════════════════
# TEST SCENARIOS
# ═══════════════════════════════════════════════════════════════════

async def test_basic_scenario_creation(tester: ScenarioTester):
    """Test 1: Create a basic scenario."""
    print("\n" + "="*60)
    print("TEST 1: Create Basic Scenario")
    print("="*60)
    
    scenario = await tester.create_scenario(
        name="Basic Growth Scenario",
        description="10% revenue growth, 5% expense increase",
        assumptions={
            "revenue_growth_pct": 10.0,
            "expense_change_pct": 5.0,
        }
    )
    
    print(f"✅ Created scenario: {scenario['id']}")
    print(f"   Name: {scenario['name']}")
    print(f"   Revenue Growth: {scenario['assumptions']['revenue_growth_pct']}%")
    print(f"   Expense Change: {scenario['assumptions']['expense_change_pct']}%")
    
    return scenario


async def test_hiring_scenario(tester: ScenarioTester):
    """Test 2: Create a hiring scenario."""
    print("\n" + "="*60)
    print("TEST 2: Create Hiring Scenario")
    print("="*60)
    
    scenario = await tester.create_scenario(
        name="Hire 5 Engineers Q3 2026",
        description="Aggressive hiring plan with 15% revenue growth",
        assumptions={
            "revenue_growth_pct": 15.0,
            "expense_change_pct": 10.0,
            "headcount_change": 5,
            "avg_salary_per_head": 80000.0,
            "customer_churn_pct": 3.0,
            "tax_rate_pct": 25.0,
        }
    )
    
    print(f"✅ Created hiring scenario: {scenario['id']}")
    print(f"   Headcount Change: +{scenario['assumptions']['headcount_change']}")
    print(f"   Avg Salary: ${scenario['assumptions']['avg_salary_per_head']:,.0f}")
    print(f"   Annual Cost: ${scenario['assumptions']['headcount_change'] * scenario['assumptions']['avg_salary_per_head']:,.0f}")
    
    return scenario


async def test_best_worst_realistic(tester: ScenarioTester):
    """Test 3: Create best/worst/realistic scenarios."""
    print("\n" + "="*60)
    print("TEST 3: Create Best/Worst/Realistic Scenarios")
    print("="*60)
    
    scenarios = []
    
    # Best case
    best = await tester.create_scenario(
        name="Best Case",
        description="Optimistic: 20% growth, low churn",
        assumptions={
            "revenue_growth_pct": 20.0,
            "expense_change_pct": 5.0,
            "customer_churn_pct": 1.0,
        }
    )
    scenarios.append(best)
    print(f"✅ Best Case: {best['assumptions']['revenue_growth_pct']}% growth")
    
    # Worst case
    worst = await tester.create_scenario(
        name="Worst Case",
        description="Pessimistic: 0% growth, high churn",
        assumptions={
            "revenue_growth_pct": 0.0,
            "expense_change_pct": 15.0,
            "customer_churn_pct": 10.0,
        }
    )
    scenarios.append(worst)
    print(f"✅ Worst Case: {worst['assumptions']['revenue_growth_pct']}% growth")
    
    # Realistic
    realistic = await tester.create_scenario(
        name="Realistic",
        description="Moderate: 10% growth, normal churn",
        assumptions={
            "revenue_growth_pct": 10.0,
            "expense_change_pct": 8.0,
            "customer_churn_pct": 3.0,
        }
    )
    scenarios.append(realistic)
    print(f"✅ Realistic: {realistic['assumptions']['revenue_growth_pct']}% growth")
    
    return scenarios


async def test_compare_scenarios(tester: ScenarioTester, scenario_ids: list):
    """Test 4: Compare multiple scenarios."""
    print("\n" + "="*60)
    print("TEST 4: Compare Scenarios")
    print("="*60)
    
    comparison = await tester.compare_scenarios(scenario_ids)
    
    print(f"✅ Compared {len(comparison['scenarios'])} scenarios")
    for scenario in comparison['scenarios']:
        print(f"   - {scenario['name']}: {scenario['assumptions']['revenue_growth_pct']}% growth")
    
    if "comparison_metrics" in comparison:
        print(f"\n📊 Comparison Metrics:")
        for key, value in comparison["comparison_metrics"].items():
            print(f"   {key}: {value}")
    
    return comparison


async def test_monte_carlo(tester: ScenarioTester, scenario_id: str):
    """Test 5: Run Monte Carlo simulation."""
    print("\n" + "="*60)
    print("TEST 5: Monte Carlo Simulation")
    print("="*60)
    
    print("Running 1,000 simulations...")
    
    result = await tester.run_monte_carlo(
        scenario_id=scenario_id,
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
            }
        }
    )
    
    print(f"✅ Monte Carlo complete:")
    print(f"   Simulations: {result['num_simulations']}")
    print(f"   Mean Outcome: {result.get('mean_outcome', 'N/A')}")
    print(f"   Std Dev: {result.get('std_dev', 'N/A')}")
    
    if "percentiles" in result:
        print(f"\n📊 Percentiles:")
        print(f"   P10: {result['percentiles'].get('p10', 'N/A')}")
        print(f"   P50 (Median): {result['percentiles'].get('p50', 'N/A')}")
        print(f"   P90: {result['percentiles'].get('p90', 'N/A')}")
    
    return result


async def test_sensitivity_analysis(tester: ScenarioTester, scenario_id: str):
    """Test 6: Run sensitivity analysis."""
    print("\n" + "="*60)
    print("TEST 6: Sensitivity Analysis")
    print("="*60)
    
    result = await tester.run_sensitivity(
        scenario_id=scenario_id,
        variables=[
            "revenue_growth_pct",
            "expense_change_pct",
            "customer_churn_pct"
        ],
        range_pct=20.0
    )
    
    print(f"✅ Sensitivity analysis complete:")
    print(f"   Variables tested: {len(result.get('variables', []))}")
    
    if "most_sensitive" in result:
        print(f"   Most sensitive: {result['most_sensitive']}")
    
    if "variables" in result:
        print(f"\n📊 Variable Impacts:")
        for var in result["variables"]:
            print(f"   {var['variable']}: Impact = {var.get('impact', 'N/A')}")
    
    return result


async def test_templates(tester: ScenarioTester):
    """Test 7: List and use templates."""
    print("\n" + "="*60)
    print("TEST 7: Scenario Templates")
    print("="*60)
    
    templates = await tester.list_templates()
    
    print(f"✅ Found {len(templates)} templates:")
    for template in templates:
        print(f"   - {template['name']} ({template['industry']})")
    
    # Get SaaS template details
    if templates:
        saas_template = await tester.get_template("saas_startup")
        print(f"\n📋 SaaS Startup Template:")
        print(f"   Revenue Growth: {saas_template['assumptions']['revenue_growth_pct']}%")
        print(f"   Headcount Change: +{saas_template['assumptions']['headcount_change']}")
        print(f"   Avg Salary: ${saas_template['assumptions']['avg_salary_per_head']:,.0f}")
        
        # Create scenario from template
        scenario = await tester.create_scenario(
            name="SaaS Growth Plan",
            description=f"Based on {saas_template['name']} template",
            assumptions=saas_template["assumptions"]
        )
        print(f"\n✅ Created scenario from template: {scenario['id']}")
        
        return scenario


async def test_list_scenarios(tester: ScenarioTester):
    """Test 8: List all scenarios."""
    print("\n" + "="*60)
    print("TEST 8: List All Scenarios")
    print("="*60)
    
    scenarios = await tester.list_scenarios()
    
    print(f"✅ Found {len(scenarios)} scenarios:")
    for scenario in scenarios[:10]:  # Show first 10
        print(f"   - {scenario['name']}: {scenario['assumptions'].get('revenue_growth_pct', 'N/A')}% growth")
    
    if len(scenarios) > 10:
        print(f"   ... and {len(scenarios) - 10} more")
    
    return scenarios


# ═══════════════════════════════════════════════════════════════════
# MAIN TEST RUNNER
# ═══════════════════════════════════════════════════════════════════

async def run_all_tests(token: Optional[str] = None):
    """Run all scenario tests."""
    print("\n" + "="*60)
    print("AI CFO — SCENARIO TESTING SUITE")
    print("="*60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    if not token:
        print("\n⚠️  WARNING: No JWT token provided!")
        print("   Tests will fail if authentication is required.")
        print("   Set JWT_TOKEN variable or pass via command line.")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    tester = ScenarioTester(API_BASE_URL, token)
    
    try:
        # Test 1: Basic scenario
        basic_scenario = await test_basic_scenario_creation(tester)
        
        # Test 2: Hiring scenario
        hiring_scenario = await test_hiring_scenario(tester)
        
        # Test 3: Best/Worst/Realistic
        bwr_scenarios = await test_best_worst_realistic(tester)
        
        # Test 4: Compare scenarios
        scenario_ids = [s['id'] for s in bwr_scenarios]
        await test_compare_scenarios(tester, scenario_ids)
        
        # Test 5: Monte Carlo
        await test_monte_carlo(tester, bwr_scenarios[1]['id'])  # Use realistic scenario
        
        # Test 6: Sensitivity analysis
        await test_sensitivity_analysis(tester, bwr_scenarios[1]['id'])
        
        # Test 7: Templates
        await test_templates(tester)
        
        # Test 8: List all scenarios
        await test_list_scenarios(tester)
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        
    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP Error: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


async def interactive_mode(token: Optional[str] = None):
    """Interactive testing mode."""
    tester = ScenarioTester(API_BASE_URL, token)
    
    print("\n" + "="*60)
    print("AI CFO — INTERACTIVE SCENARIO TESTING")
    print("="*60)
    
    while True:
        print("\nOptions:")
        print("1. Create scenario")
        print("2. List scenarios")
        print("3. Compare scenarios")
        print("4. Run Monte Carlo")
        print("5. Run sensitivity analysis")
        print("6. List templates")
        print("7. Run all tests")
        print("0. Exit")
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            name = input("Scenario name: ")
            description = input("Description: ")
            revenue_growth = float(input("Revenue growth %: "))
            expense_change = float(input("Expense change %: "))
            
            scenario = await tester.create_scenario(
                name=name,
                description=description,
                assumptions={
                    "revenue_growth_pct": revenue_growth,
                    "expense_change_pct": expense_change,
                }
            )
            print(f"✅ Created: {scenario['id']}")
        
        elif choice == "2":
            scenarios = await tester.list_scenarios()
            print(f"\n{len(scenarios)} scenarios:")
            for s in scenarios:
                print(f"  {s['id']}: {s['name']}")
        
        elif choice == "7":
            await run_all_tests(token)
        
        else:
            print("Not implemented yet")


if __name__ == "__main__":
    import sys
    
    # Check for token in command line
    if len(sys.argv) > 1:
        JWT_TOKEN = sys.argv[1]
    
    # Check for interactive mode
    if len(sys.argv) > 2 and sys.argv[2] == "--interactive":
        asyncio.run(interactive_mode(JWT_TOKEN))
    else:
        asyncio.run(run_all_tests(JWT_TOKEN))
