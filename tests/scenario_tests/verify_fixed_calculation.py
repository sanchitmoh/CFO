#!/usr/bin/env python3
"""
Verify FIXED Scenario Calculation
Checking if the growth rate bug has been resolved
"""

print("="*70)
print("FIXED SCENARIO CALCULATION VERIFICATION")
print("="*70)

# New scenario data (after fix)
scenario = {
    "name": "Q3 2026 Growth Plan",
    "assumptions": {
        "revenue_growth_pct": 0.15,  # 15%
        "expense_change_pct": 0.1,   # 10%
        "one_time_income": 800000.0,
        "one_time_expense": 25000000.0,
    }
}

results = {
    "month_1": {
        "income": 1092891.08,
        "expenses": 29888135.43,
        "net": -28795244.34
    },
    "month_2": {
        "income": 336824.75,
        "expenses": 5376948.97,
        "net": -5040124.22
    },
    "month_3": {
        "income": 387348.46,
        "expenses": 5914643.87,
        "net": -5527295.41
    },
    "month_4": {
        "income": 445450.73,
        "expenses": 6506108.25,
        "net": -6060657.53
    },
    "month_12": {
        "income": 1362643.96,
        "expenses": 13946420.85,
        "net": -12583776.89
    }
}

print(f"\nScenario: {scenario['name']}")
print(f"Revenue Growth: {scenario['assumptions']['revenue_growth_pct']*100}% per month")
print(f"Expense Growth: {scenario['assumptions']['expense_change_pct']*100}% per month")

print("\n" + "="*70)
print("MONTH 1 ANALYSIS")
print("="*70)

# Extract recurring amounts from Month 1
recurring_income_m1 = results['month_1']['income'] - scenario['assumptions']['one_time_income']
recurring_expense_m1 = results['month_1']['expenses'] - scenario['assumptions']['one_time_expense']

print(f"\n📊 Month 1 Breakdown:")
print(f"   Total Income: ${results['month_1']['income']:,.2f}")
print(f"   - One-time Income: ${scenario['assumptions']['one_time_income']:,.2f}")
print(f"   = Recurring Income: ${recurring_income_m1:,.2f}")

print(f"\n   Total Expenses: ${results['month_1']['expenses']:,.2f}")
print(f"   - One-time Expense: ${scenario['assumptions']['one_time_expense']:,.2f}")
print(f"   = Recurring Expenses: ${recurring_expense_m1:,.2f}")

print("\n" + "="*70)
print("GROWTH VERIFICATION (THE CRITICAL TEST)")
print("="*70)

# Test Month 2
print(f"\n🔍 Month 2 - Testing 15% Revenue Growth:")
expected_income_m2 = recurring_income_m1 * (1 + scenario['assumptions']['revenue_growth_pct'])
actual_income_m2 = results['month_2']['income']
diff_m2 = actual_income_m2 - expected_income_m2

print(f"   Expected: ${recurring_income_m1:,.2f} × 1.15 = ${expected_income_m2:,.2f}")
print(f"   Actual: ${actual_income_m2:,.2f}")
print(f"   Difference: ${diff_m2:,.2f}")

if abs(diff_m2) < 1:
    print(f"   ✅ CORRECT! Growth rate applied properly!")
else:
    print(f"   ❌ ERROR: Growth rate not applied correctly")

# Test Month 3
print(f"\n🔍 Month 3 - Testing Compounding Growth:")
expected_income_m3 = expected_income_m2 * (1 + scenario['assumptions']['revenue_growth_pct'])
actual_income_m3 = results['month_3']['income']
diff_m3 = actual_income_m3 - expected_income_m3

print(f"   Expected: ${expected_income_m2:,.2f} × 1.15 = ${expected_income_m3:,.2f}")
print(f"   Actual: ${actual_income_m3:,.2f}")
print(f"   Difference: ${diff_m3:,.2f}")

if abs(diff_m3) < 1:
    print(f"   ✅ CORRECT! Compounding growth works!")
else:
    print(f"   ❌ ERROR: Compounding not working")

# Test expenses
print(f"\n🔍 Month 2 - Testing 10% Expense Growth:")
expected_expense_m2 = recurring_expense_m1 * (1 + scenario['assumptions']['expense_change_pct'])
actual_expense_m2 = results['month_2']['expenses']
diff_exp_m2 = actual_expense_m2 - expected_expense_m2

print(f"   Expected: ${recurring_expense_m1:,.2f} × 1.10 = ${expected_expense_m2:,.2f}")
print(f"   Actual: ${actual_expense_m2:,.2f}")
print(f"   Difference: ${diff_exp_m2:,.2f}")

if abs(diff_exp_m2) < 1:
    print(f"   ✅ CORRECT! Expense growth applied properly!")
else:
    print(f"   ❌ ERROR: Expense growth not applied correctly")

print("\n" + "="*70)
print("GROWTH TRAJECTORY ANALYSIS")
print("="*70)

# Calculate growth rates between months
months = [
    ("Month 1→2", recurring_income_m1, results['month_2']['income']),
    ("Month 2→3", results['month_2']['income'], results['month_3']['income']),
    ("Month 3→4", results['month_3']['income'], results['month_4']['income']),
]

print(f"\n📈 Income Growth Rates:")
all_correct = True
for label, prev, curr in months:
    growth_rate = (curr - prev) / prev
    expected_rate = scenario['assumptions']['revenue_growth_pct']
    diff = abs(growth_rate - expected_rate)
    
    status = "✅" if diff < 0.001 else "❌"
    print(f"   {label}: {growth_rate*100:.2f}% (expected {expected_rate*100:.0f}%) {status}")
    
    if diff >= 0.001:
        all_correct = False

if all_correct:
    print(f"\n   ✅ ALL GROWTH RATES CORRECT!")
else:
    print(f"\n   ❌ SOME GROWTH RATES INCORRECT")

print("\n" + "="*70)
print("LONG-TERM PROJECTION")
print("="*70)

# Calculate what Month 12 should be
expected_income_m12 = recurring_income_m1 * ((1 + scenario['assumptions']['revenue_growth_pct']) ** 11)
actual_income_m12 = results['month_12']['income']
diff_m12 = actual_income_m12 - expected_income_m12

print(f"\n📊 Month 12 Projection:")
print(f"   Starting: ${recurring_income_m1:,.2f}")
print(f"   Growth: 15% per month for 11 months")
print(f"   Expected: ${recurring_income_m1:,.2f} × (1.15^11) = ${expected_income_m12:,.2f}")
print(f"   Actual: ${actual_income_m12:,.2f}")
print(f"   Difference: ${diff_m12:,.2f}")

if abs(diff_m12) < 100:
    print(f"   ✅ CORRECT! Long-term compounding works!")
else:
    print(f"   ⚠️  Small difference (acceptable rounding)")

print("\n" + "="*70)
print("COMPARISON: BEFORE vs AFTER FIX")
print("="*70)

print(f"\n📊 Month 2 Income:")
print(f"   BEFORE FIX: $255,069.93 (NO GROWTH)")
print(f"   AFTER FIX:  ${results['month_2']['income']:,.2f} (15% GROWTH)")
print(f"   Improvement: ${results['month_2']['income'] - 255069.93:,.2f}")

print(f"\n📊 Month 12 Income:")
print(f"   BEFORE FIX: $255,069.93 (FLAT)")
print(f"   AFTER FIX:  ${results['month_12']['income']:,.2f} (COMPOUNDING)")
print(f"   Improvement: ${results['month_12']['income'] - 255069.93:,.2f}")

growth_factor = results['month_12']['income'] / recurring_income_m1
print(f"\n📈 Total Growth Factor:")
print(f"   Month 1 to Month 12: {growth_factor:.2f}x")
print(f"   Expected (1.15^11): {(1.15**11):.2f}x")

if abs(growth_factor - (1.15**11)) < 0.1:
    print(f"   ✅ MATCHES EXPECTED!")
else:
    print(f"   ❌ DOESN'T MATCH")

print("\n" + "="*70)
print("FINAL VERDICT")
print("="*70)

# Check all conditions
checks = [
    ("Month 2 growth rate", abs(diff_m2) < 1),
    ("Month 3 growth rate", abs(diff_m3) < 1),
    ("Expense growth rate", abs(diff_exp_m2) < 1),
    ("All monthly growth rates", all_correct),
    ("Long-term compounding", abs(diff_m12) < 100),
]

all_passed = all(check[1] for check in checks)

print(f"\n✅ Verification Results:")
for check_name, passed in checks:
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"   {check_name}: {status}")

print("\n" + "="*70)

if all_passed:
    print("🎉 SUCCESS! THE BUG HAS BEEN FIXED!")
    print("="*70)
    print("\n✅ All calculations are now CORRECT:")
    print("   • Growth rates are applied properly")
    print("   • Compounding works correctly")
    print("   • Long-term projections are accurate")
    print("   • The /100 division has been removed")
    print("\n🚀 The scenario planning feature is now production-ready!")
else:
    print("❌ ISSUE DETECTED")
    print("="*70)
    print("\nSome calculations are still incorrect.")
    print("Please review the differences above.")

print("\n" + "="*70)
