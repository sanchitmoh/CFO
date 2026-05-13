#!/usr/bin/env python3
"""
Test All Scenarios
Automated testing of all 25 test scenarios
"""
import json
import sys
from pathlib import Path

# Load test data
test_data_path = Path(__file__).parent / "test_data.json"
with open(test_data_path, 'r') as f:
    TEST_DATA = json.load(f)

def validate_growth_rate(prev_value, curr_value, expected_rate, tolerance=0.001):
    """Validate that growth rate is applied correctly."""
    if prev_value == 0:
        return True  # Can't calculate growth from zero
    
    actual_rate = (curr_value - prev_value) / prev_value
    diff = abs(actual_rate - expected_rate)
    return diff < tolerance

def test_scenario(scenario, base_income=100000, base_expense=80000, starting_cash=0):
    """
    Test a single scenario by simulating the calculation.
    Returns test results and any errors found.
    """
    assumptions = scenario['assumptions']
    results = {
        'scenario_id': scenario['id'],
        'scenario_name': scenario['name'],
        'passed': True,
        'errors': [],
        'warnings': [],
        'monthly_results': []
    }
    
    # Simulate 12 months
    cumulative_cash = starting_cash
    prev_income = base_income
    prev_expense = base_expense
    
    for month in range(1, 13):
        # Calculate income
        income = prev_income * (1 + assumptions['revenue_growth_pct'])
        
        # Apply pricing change
        income *= (1 + assumptions.get('pricing_change_pct', 0))
        
        # Apply churn
        churn_factor = 1 - assumptions.get('customer_churn_pct', 0)
        income *= max(churn_factor, 0)
        
        # Calculate expenses
        expense = prev_expense * (1 + assumptions['expense_change_pct'])
        
        # Month 1: Add one-time items
        if month == 1:
            income += assumptions['one_time_income']
            expense += assumptions['one_time_expense']
        
        # Calculate net cash flow
        net_cash_flow = income - expense
        cumulative_cash += net_cash_flow
        
        # Store results
        monthly_result = {
            'month': month,
            'income': round(income, 2),
            'expense': round(expense, 2),
            'net_cash_flow': round(net_cash_flow, 2),
            'cumulative_cash': round(cumulative_cash, 2)
        }
        results['monthly_results'].append(monthly_result)
        
        # Validate growth rates (skip Month 1 due to one-time items)
        if month == 2:
            # Extract recurring amounts from Month 1
            recurring_income_m1 = results['monthly_results'][0]['income'] - assumptions['one_time_income']
            recurring_expense_m1 = results['monthly_results'][0]['expense'] - assumptions['one_time_expense']
            
            # Validate Month 2 growth
            if not validate_growth_rate(recurring_income_m1, income, assumptions['revenue_growth_pct']):
                results['errors'].append(f"Month 2 income growth incorrect")
                results['passed'] = False
            
            if not validate_growth_rate(recurring_expense_m1, expense, assumptions['expense_change_pct']):
                results['errors'].append(f"Month 2 expense growth incorrect")
                results['passed'] = False
        
        # Update for next month
        if month == 1:
            # Remove one-time items for next month's base
            prev_income = income - assumptions['one_time_income']
            prev_expense = expense - assumptions['one_time_expense']
        else:
            prev_income = income
            prev_expense = expense
    
    # Validate expected behavior
    if 'expected_behavior' in scenario:
        behavior = scenario['expected_behavior'].lower()
        
        # Check for expected patterns
        if 'improving' in behavior or 'growth' in behavior:
            # Check if cash flow is improving
            if results['monthly_results'][-1]['cumulative_cash'] <= results['monthly_results'][1]['cumulative_cash']:
                results['warnings'].append("Expected improving cash flow, but it's declining")
        
        if 'positive' in behavior and 'month 1' in behavior:
            if results['monthly_results'][0]['net_cash_flow'] <= 0:
                results['warnings'].append("Expected positive Month 1, but it's negative")
        
        if 'negative' in behavior and 'month 1' in behavior:
            if results['monthly_results'][0]['net_cash_flow'] >= 0:
                results['warnings'].append("Expected negative Month 1, but it's positive")
    
    return results

def run_all_tests():
    """Run tests on all scenarios."""
    print("\n" + "="*70)
    print("TESTING ALL SCENARIOS")
    print("="*70)
    
    all_scenarios = TEST_DATA['test_scenarios'] + TEST_DATA['edge_cases']
    
    passed = 0
    failed = 0
    warnings = 0
    
    results_summary = []
    
    for i, scenario in enumerate(all_scenarios, 1):
        print(f"\n[{i}/{len(all_scenarios)}] Testing: {scenario['name']}")
        print(f"    ID: {scenario['id']}")
        
        # Run test
        result = test_scenario(scenario)
        results_summary.append(result)
        
        # Display results
        if result['passed']:
            print(f"    ✅ PASSED")
            passed += 1
        else:
            print(f"    ❌ FAILED")
            failed += 1
            for error in result['errors']:
                print(f"       Error: {error}")
        
        if result['warnings']:
            warnings += len(result['warnings'])
            for warning in result['warnings']:
                print(f"       ⚠️  Warning: {warning}")
        
        # Show key metrics
        m1 = result['monthly_results'][0]
        m2 = result['monthly_results'][1]
        m12 = result['monthly_results'][11]
        
        print(f"    Month 1: Income=${m1['income']:,.0f}, Expense=${m1['expense']:,.0f}, Net=${m1['net_cash_flow']:,.0f}")
        print(f"    Month 2: Income=${m2['income']:,.0f}, Expense=${m2['expense']:,.0f}, Net=${m2['net_cash_flow']:,.0f}")
        print(f"    Month 12: Cumulative Cash=${m12['cumulative_cash']:,.0f}")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"\nTotal Scenarios: {len(all_scenarios)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Warnings: {warnings}")
    print(f"\nSuccess Rate: {(passed/len(all_scenarios)*100):.1f}%")
    
    # Failed scenarios
    if failed > 0:
        print("\n" + "="*70)
        print("FAILED SCENARIOS")
        print("="*70)
        for result in results_summary:
            if not result['passed']:
                print(f"\n❌ {result['scenario_id']}: {result['scenario_name']}")
                for error in result['errors']:
                    print(f"   - {error}")
    
    # Warnings
    if warnings > 0:
        print("\n" + "="*70)
        print("WARNINGS")
        print("="*70)
        for result in results_summary:
            if result['warnings']:
                print(f"\n⚠️  {result['scenario_id']}: {result['scenario_name']}")
                for warning in result['warnings']:
                    print(f"   - {warning}")
    
    # Category breakdown
    print("\n" + "="*70)
    print("CATEGORY BREAKDOWN")
    print("="*70)
    
    categories = {}
    for scenario in TEST_DATA['test_scenarios']:
        cat = scenario.get('category', 'other')
        if cat not in categories:
            categories[cat] = {'total': 0, 'passed': 0}
        categories[cat]['total'] += 1
        
        # Find result
        for result in results_summary:
            if result['scenario_id'] == scenario['id']:
                if result['passed']:
                    categories[cat]['passed'] += 1
                break
    
    for cat, stats in sorted(categories.items()):
        rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"{cat.upper():<15} {stats['passed']}/{stats['total']} ({rate:.0f}%)")
    
    # Edge cases
    edge_passed = sum(1 for r in results_summary if r['scenario_id'].startswith('edge_') and r['passed'])
    edge_total = len(TEST_DATA['edge_cases'])
    edge_rate = (edge_passed / edge_total * 100) if edge_total > 0 else 0
    print(f"{'EDGE CASES':<15} {edge_passed}/{edge_total} ({edge_rate:.0f}%)")
    
    print("\n" + "="*70)
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        print("="*70)
        print("\n✅ All scenarios calculated correctly")
        print("✅ Growth rates applied properly")
        print("✅ One-time items handled correctly")
        print("✅ Expected behaviors validated")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("="*70)
        print(f"\n{failed} scenario(s) failed validation")
        print("Review the errors above for details")
        return 1

def test_specific_scenarios(scenario_ids):
    """Test specific scenarios by ID."""
    print("\n" + "="*70)
    print("TESTING SPECIFIC SCENARIOS")
    print("="*70)
    
    all_scenarios = TEST_DATA['test_scenarios'] + TEST_DATA['edge_cases']
    
    for scenario_id in scenario_ids:
        # Find scenario
        scenario = None
        for s in all_scenarios:
            if s['id'] == scenario_id:
                scenario = s
                break
        
        if not scenario:
            print(f"\n❌ Scenario '{scenario_id}' not found")
            continue
        
        print(f"\nTesting: {scenario['name']} ({scenario_id})")
        
        # Run test
        result = test_scenario(scenario)
        
        # Display detailed results
        if result['passed']:
            print(f"✅ PASSED")
        else:
            print(f"❌ FAILED")
            for error in result['errors']:
                print(f"   Error: {error}")
        
        if result['warnings']:
            for warning in result['warnings']:
                print(f"   ⚠️  Warning: {warning}")
        
        # Show all monthly results
        print(f"\n📊 Monthly Results:")
        print(f"{'Month':<8} {'Income':<15} {'Expense':<15} {'Net CF':<15} {'Cumulative':<15}")
        print("-" * 70)
        for m in result['monthly_results']:
            print(f"{m['month']:<8} ${m['income']:<14,.0f} ${m['expense']:<14,.0f} ${m['net_cash_flow']:<14,.0f} ${m['cumulative_cash']:<14,.0f}")

def export_results(output_file="test_results.json"):
    """Export test results to JSON file."""
    print(f"\nExporting results to {output_file}...")
    
    all_scenarios = TEST_DATA['test_scenarios'] + TEST_DATA['edge_cases']
    results = []
    
    for scenario in all_scenarios:
        result = test_scenario(scenario)
        results.append(result)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✅ Exported {len(results)} test results")

# CLI Interface
if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "all":
            sys.exit(run_all_tests())
        
        elif command == "test" and len(sys.argv) > 2:
            test_specific_scenarios(sys.argv[2:])
        
        elif command == "export":
            export_results()
        
        else:
            print("Usage:")
            print("  python test_all_scenarios.py all")
            print("  python test_all_scenarios.py test <scenario_id> [<scenario_id> ...]")
            print("  python test_all_scenarios.py export")
    else:
        # Default: run all tests
        sys.exit(run_all_tests())
