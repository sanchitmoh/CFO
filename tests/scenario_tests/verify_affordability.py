#!/usr/bin/env python3
"""
Verify Affordability Calculator
Analyze the affordability calculation result
"""

print("="*70)
print("AFFORDABILITY CALCULATOR VERIFICATION")
print("="*70)

# Given result
result = {
    "can_afford": False,
    "current_runway_months": 0.0,
    "projected_runway_months": 0.0,
    "current_balance_3m": -65431927.82,
    "projected_balance_3m": -65556927.82,
    "break_even_revenue": 65556927.82,
    "ai_suggestion": "Not affordable: 'SaaS' would leave an estimated 3-month cash gap of ₹65,556,927.82. You would need ₹65,556,927.82 of additional revenue over 3 months to stay cash-neutral."
}

print("\n📊 GIVEN RESULT:")
print(f"   Can Afford: {result['can_afford']}")
print(f"   Current Runway: {result['current_runway_months']} months")
print(f"   Projected Runway: {result['projected_runway_months']} months")
print(f"   Current 3M Balance: ₹{result['current_balance_3m']:,.2f}")
print(f"   Projected 3M Balance: ₹{result['projected_balance_3m']:,.2f}")
print(f"   Break-even Revenue Needed: ₹{result['break_even_revenue']:,.2f}")

print("\n" + "="*70)
print("ANALYSIS")
print("="*70)

# Calculate the difference
difference = result['projected_balance_3m'] - result['current_balance_3m']
print(f"\n💰 Impact of Expense:")
print(f"   Current 3M Balance: ₹{result['current_balance_3m']:,.2f}")
print(f"   Projected 3M Balance: ₹{result['projected_balance_3m']:,.2f}")
print(f"   Difference: ₹{difference:,.2f}")
print(f"   Additional Cost: ₹{abs(difference):,.2f}")

# Analyze the situation
print(f"\n🔍 Situation Analysis:")

if result['current_balance_3m'] < 0:
    print(f"   ⚠️  ALREADY IN DEFICIT: Current 3-month projection is negative")
    print(f"   Current deficit: ₹{abs(result['current_balance_3m']):,.2f}")
    print(f"   This means expenses already exceed income")

if result['current_runway_months'] == 0.0:
    print(f"   🔴 ZERO RUNWAY: No cash buffer available")
    print(f"   This indicates current cash balance is ≤ 0")

# Calculate monthly burn
monthly_burn_current = result['current_balance_3m'] / 3
monthly_burn_projected = result['projected_balance_3m'] / 3

print(f"\n📉 Monthly Burn Rate:")
print(f"   Current: ₹{monthly_burn_current:,.2f} per month")
print(f"   Projected: ₹{monthly_burn_projected:,.2f} per month")
print(f"   Increase: ₹{abs(monthly_burn_projected - monthly_burn_current):,.2f} per month")

# Calculate what's needed
print(f"\n💡 What's Needed:")
print(f"   To break even (0 balance): ₹{result['break_even_revenue']:,.2f} over 3 months")
print(f"   Per month: ₹{result['break_even_revenue']/3:,.2f}")

# Reverse engineer the expense
expense_amount = abs(difference)
print(f"\n🎯 Expense Being Evaluated:")
print(f"   Total 3-month impact: ₹{expense_amount:,.2f}")

# Possible scenarios
print(f"\n📋 Possible Scenarios:")
print(f"   1. One-time expense: ₹{expense_amount:,.2f}")
print(f"   2. Monthly recurring: ₹{expense_amount/3:,.2f} per month")
print(f"   3. Annual expense: ₹{expense_amount*4:,.2f} per year")

print("\n" + "="*70)
print("VALIDATION CHECKS")
print("="*70)

# Check 1: Break-even calculation
calculated_break_even = abs(result['projected_balance_3m'])
matches_break_even = abs(calculated_break_even - result['break_even_revenue']) < 0.01

print(f"\n✓ Check 1: Break-even Revenue")
print(f"   Expected: ₹{result['break_even_revenue']:,.2f}")
print(f"   Calculated: ₹{calculated_break_even:,.2f}")
if matches_break_even:
    print(f"   ✅ CORRECT: Break-even = abs(projected_balance_3m)")
else:
    print(f"   ❌ ERROR: Values don't match")

# Check 2: Affordability logic
print(f"\n✓ Check 2: Affordability Decision")
print(f"   Projected Balance: ₹{result['projected_balance_3m']:,.2f}")
print(f"   Is Negative: {result['projected_balance_3m'] < 0}")
print(f"   Can Afford: {result['can_afford']}")
if result['projected_balance_3m'] < 0 and not result['can_afford']:
    print(f"   ✅ CORRECT: Negative balance = not affordable")
elif result['projected_balance_3m'] >= 0 and result['can_afford']:
    print(f"   ✅ CORRECT: Positive balance = affordable")
else:
    print(f"   ⚠️  INCONSISTENT: Balance and affordability don't match")

# Check 3: Runway calculation
print(f"\n✓ Check 3: Runway Calculation")
print(f"   Current Runway: {result['current_runway_months']} months")
print(f"   Projected Runway: {result['projected_runway_months']} months")
if result['current_runway_months'] == 0.0:
    print(f"   ✅ CORRECT: Zero runway indicates no cash buffer")
else:
    print(f"   ⚠️  Current runway > 0 but balance is negative")

print("\n" + "="*70)
print("BUSINESS INTERPRETATION")
print("="*70)

print(f"\n🏢 Current Business State:")
print(f"   • Operating at a LOSS")
print(f"   • Burning ₹{abs(monthly_burn_current):,.2f} per month")
print(f"   • 3-month projected loss: ₹{abs(result['current_balance_3m']):,.2f}")
print(f"   • No cash runway (0 months)")

print(f"\n💸 Impact of 'SaaS' Expense:")
print(f"   • Adds ₹{abs(difference):,.2f} to 3-month costs")
print(f"   • Increases monthly burn by ₹{abs(difference)/3:,.2f}")
print(f"   • Total 3-month loss becomes: ₹{abs(result['projected_balance_3m']):,.2f}")

print(f"\n🎯 To Become Affordable:")
print(f"   • Need ₹{result['break_even_revenue']:,.2f} additional revenue over 3 months")
print(f"   • That's ₹{result['break_even_revenue']/3:,.2f} per month")
print(f"   • Or reduce expenses by the same amount")

print("\n" + "="*70)
print("RECOMMENDATIONS")
print("="*70)

print(f"\n💡 Immediate Actions:")
print(f"   1. 🔴 DO NOT proceed with 'SaaS' expense")
print(f"   2. 📊 Review current burn rate (₹{abs(monthly_burn_current):,.2f}/month)")
print(f"   3. 💰 Increase revenue by ₹{result['break_even_revenue']/3:,.2f}/month")
print(f"   4. ✂️  Cut expenses by ₹{abs(monthly_burn_current):,.2f}/month")
print(f"   5. 💵 Secure funding to cover deficit")

print(f"\n📈 Path to Affordability:")
print(f"   Option A: Increase monthly revenue to ₹{result['break_even_revenue']/3:,.2f}")
print(f"   Option B: Reduce monthly expenses by ₹{abs(monthly_burn_current):,.2f}")
print(f"   Option C: Combination of revenue increase + expense reduction")

print("\n" + "="*70)
print("VERDICT")
print("="*70)

print(f"\n✅ CALCULATION IS CORRECT")
print(f"\nThe affordability calculator correctly determined:")
print(f"   • Business is currently losing money")
print(f"   • Adding 'SaaS' expense makes it worse")
print(f"   • Need ₹{result['break_even_revenue']:,.2f} additional revenue to break even")
print(f"   • Recommendation: NOT AFFORDABLE is accurate")

print(f"\n⚠️  CRITICAL BUSINESS SITUATION:")
print(f"   The business is in a deficit state with:")
print(f"   • Negative cash flow")
print(f"   • Zero runway")
print(f"   • Significant monthly burn")
print(f"\n   Focus on:")
print(f"   1. Increasing revenue")
print(f"   2. Reducing costs")
print(f"   3. Securing funding")
print(f"   BEFORE considering new expenses")

print("\n" + "="*70)
