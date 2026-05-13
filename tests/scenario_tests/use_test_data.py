#!/usr/bin/env python3
"""
Use Test Data for Scenario Testing
Load and use predefined test scenarios
"""
import json
import sys
from pathlib import Path

# Load test data
test_data_path = Path(__file__).parent / "test_data.json"
with open(test_data_path, 'r') as f:
    TEST_DATA = json.load(f)

def list_scenarios():
    """List all available test scenarios."""
    print("\n" + "="*70)
    print("AVAILABLE TEST SCENARIOS")
    print("="*70)
    
    scenarios = TEST_DATA['test_scenarios']
    
    # Group by category
    categories = {}
    for scenario in scenarios:
        cat = scenario.get('category', 'other')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(scenario)
    
    for category, scens in sorted(categories.items()):
        print(f"\n📁 {category.upper()}")
        for s in scens:
            print(f"   {s['id']}: {s['name']}")
            print(f"      {s['description']}")
    
    print(f"\n📊 Total: {len(scenarios)} test scenarios")
    print(f"📊 Edge Cases: {len(TEST_DATA['edge_cases'])} scenarios")


def get_scenario(scenario_id):
    """Get a specific test scenario by ID."""
    for scenario in TEST_DATA['test_scenarios']:
        if scenario['id'] == scenario_id:
            return scenario
    
    for scenario in TEST_DATA['edge_cases']:
        if scenario['id'] == scenario_id:
            return scenario
    
    return None


def print_scenario(scenario_id):
    """Print details of a specific scenario."""
    scenario = get_scenario(scenario_id)
    
    if not scenario:
        print(f"❌ Scenario '{scenario_id}' not found")
        return
    
    print("\n" + "="*70)
    print(f"SCENARIO: {scenario['name']}")
    print("="*70)
    print(f"\nID: {scenario['id']}")
    print(f"Description: {scenario['description']}")
    if 'category' in scenario:
        print(f"Category: {scenario['category']}")
    
    print(f"\n📊 Assumptions:")
    assumptions = scenario['assumptions']
    print(f"   Revenue Growth: {assumptions['revenue_growth_pct']*100:.1f}% per month")
    print(f"   Expense Change: {assumptions['expense_change_pct']*100:.1f}% per month")
    print(f"   One-time Income: ${assumptions['one_time_income']:,.2f}")
    print(f"   One-time Expense: ${assumptions['one_time_expense']:,.2f}")
    
    if 'expected_behavior' in scenario:
        print(f"\n💡 Expected Behavior:")
        print(f"   {scenario['expected_behavior']}")
    
    print("\n📋 JSON for API:")
    print(json.dumps(assumptions, indent=2))


def generate_curl_command(scenario_id, api_url="http://localhost:8000", token="YOUR_TOKEN"):
    """Generate a cURL command to create this scenario."""
    scenario = get_scenario(scenario_id)
    
    if not scenario:
        print(f"❌ Scenario '{scenario_id}' not found")
        return
    
    payload = {
        "name": scenario['name'],
        "description": scenario['description'],
        "assumptions": scenario['assumptions']
    }
    
    print("\n" + "="*70)
    print(f"CURL COMMAND FOR: {scenario['name']}")
    print("="*70)
    print(f"\ncurl -X POST {api_url}/api/scenarios \\")
    print(f'  -H "Authorization: Bearer {token}" \\')
    print(f'  -H "Content-Type: application/json" \\')
    print(f"  -d '{json.dumps(payload)}'")


def generate_python_code(scenario_id):
    """Generate Python code to create this scenario."""
    scenario = get_scenario(scenario_id)
    
    if not scenario:
        print(f"❌ Scenario '{scenario_id}' not found")
        return
    
    print("\n" + "="*70)
    print(f"PYTHON CODE FOR: {scenario['name']}")
    print("="*70)
    print("""
import httpx
import asyncio

async def create_scenario():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/scenarios",
            headers={
                "Authorization": "Bearer YOUR_TOKEN",
                "Content-Type": "application/json"
            },
            json={""")
    print(f'                "name": "{scenario["name"]}",')
    print(f'                "description": "{scenario["description"]}",')
    print(f'                "assumptions": {json.dumps(scenario["assumptions"], indent=20)}')
    print("""            }
        )
        return response.json()

# Run
result = asyncio.run(create_scenario())
print(f"Created scenario: {result['id']}")
""")


def compare_scenarios(scenario_ids):
    """Compare multiple scenarios side by side."""
    scenarios = [get_scenario(sid) for sid in scenario_ids]
    scenarios = [s for s in scenarios if s is not None]
    
    if not scenarios:
        print("❌ No valid scenarios found")
        return
    
    print("\n" + "="*70)
    print("SCENARIO COMPARISON")
    print("="*70)
    
    print(f"\n{'Metric':<30}", end="")
    for s in scenarios:
        print(f"{s['id']:<15}", end="")
    print()
    print("-" * 70)
    
    # Compare key metrics
    metrics = [
        ("Revenue Growth %", lambda s: s['assumptions']['revenue_growth_pct'] * 100),
        ("Expense Change %", lambda s: s['assumptions']['expense_change_pct'] * 100),
        ("One-time Income", lambda s: s['assumptions']['one_time_income']),
        ("One-time Expense", lambda s: s['assumptions']['one_time_expense']),
    ]
    
    for metric_name, metric_func in metrics:
        print(f"{metric_name:<30}", end="")
        for s in scenarios:
            value = metric_func(s)
            if metric_name.endswith('%'):
                print(f"{value:>13.1f}%", end=" ")
            else:
                print(f"${value:>13,.0f}", end=" ")
        print()


def export_for_testing(output_file="test_scenarios_export.json"):
    """Export all scenarios in a format ready for automated testing."""
    export_data = {
        "scenarios": TEST_DATA['test_scenarios'],
        "edge_cases": TEST_DATA['edge_cases'],
        "total_count": len(TEST_DATA['test_scenarios']) + len(TEST_DATA['edge_cases'])
    }
    
    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"✅ Exported {export_data['total_count']} scenarios to {output_file}")


# CLI Interface
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n" + "="*70)
        print("SCENARIO TEST DATA UTILITY")
        print("="*70)
        print("\nUsage:")
        print("  python use_test_data.py list")
        print("  python use_test_data.py show <scenario_id>")
        print("  python use_test_data.py curl <scenario_id>")
        print("  python use_test_data.py python <scenario_id>")
        print("  python use_test_data.py compare <id1> <id2> <id3>")
        print("  python use_test_data.py export")
        print("\nExamples:")
        print("  python use_test_data.py list")
        print("  python use_test_data.py show test_001")
        print("  python use_test_data.py curl test_003")
        print("  python use_test_data.py compare test_001 test_002 test_010")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_scenarios()
    
    elif command == "show" and len(sys.argv) >= 3:
        print_scenario(sys.argv[2])
    
    elif command == "curl" and len(sys.argv) >= 3:
        generate_curl_command(sys.argv[2])
    
    elif command == "python" and len(sys.argv) >= 3:
        generate_python_code(sys.argv[2])
    
    elif command == "compare" and len(sys.argv) >= 4:
        compare_scenarios(sys.argv[3:])
    
    elif command == "export":
        export_for_testing()
    
    else:
        print("❌ Invalid command or missing arguments")
        print("Run without arguments to see usage")
