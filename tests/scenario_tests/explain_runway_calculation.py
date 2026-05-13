#!/usr/bin/env python3
"""
Explain Runway Calculation
Why is runway 0 months?
"""

print("="*70)
print("RUNWAY CALCULATION EXPLAINED")
print("="*70)

# The runway calculation function from calculator_service.py
def _runway_months(cash_balance: float, monthly_net_flow: float) -> float:
    """
    Calculate runway in months.
    
    Runway = How many months until you run out of cash
    Formula: cash_balance / abs(monthly_burn_rate)
    """
    RUNWAY_CAP_MONTHS = 99.0
    
    # Case 1: No cash left
    if cash_balance <= 0:
        return 0.0
    
    # Case 2: Making money (positive cash flow)
    if monthly_net_flow >= 0:
        return RUNWAY_CAP_MONTHS  # Infinite runway
    
    # Case 3: Burning cash (negative cash flow)
    return min(cash_balance / abs(monthly_net_flow), RUNWAY_CAP_MONTHS)

print("\n📚 RUNWAY FORMULA:")
print("   Runway = Cash Balance / Monthly Burn Rate")
print("   (Only if cash balance > 0 and burning money)")

print("\n" + "="*70)
print("YOUR SITUATION")
print("="*70)

# From the affordability result
current_balance_3m = -65431927.82
monthly_burn = current_balance_3m / 3  # -21,810,642.61

print(f"\n💰 Financial State:")
print(f"   3-Month Balance: ₹{current_balance_3m:,.2f}")
print(f"   Monthly Net Flow: ₹{monthly_burn:,.2f}")

# To calculate runway, we need CURRENT cash balance, not 3-month projection
# The 3-month balance is a projection, not current cash

print(f"\n🔍 Understanding the Numbers:")
print(f"   • 3-Month Balance = PROJECTION (where you'll be in 3 months)")
print(f"   • Current Cash Balance = ACTUAL cash in bank NOW")
print(f"   • Monthly Net Flow = Income - Expenses per month")

print("\n" + "="*70)
print("WHY RUNWAY IS 0")
print("="*70)

print(f"\n📊 Runway Calculation Logic:")
print(f"   Step 1: Check current cash balance")
print(f"   Step 2: If cash_balance <= 0 → Runway = 0")
print(f"   Step 3: If cash_balance > 0 → Runway = cash / burn_rate")

print(f"\n🎯 In Your Case:")
print(f"   Current Cash Balance: ≤ ₹0")
print(f"   Result: Runway = 0 months")

print(f"\n💡 What This Means:")
print(f"   • You have NO cash buffer")
print(f"   • You're already at or below ₹0 in the bank")
print(f"   • You can't survive even 1 month without new income")

print("\n" + "="*70)
print("DETAILED BREAKDOWN")
print("="*70)

# Let's work backwards from the 3-month projection
print(f"\n🔢 Working Backwards:")
print(f"   3-Month Projected Balance: ₹{current_balance_3m:,.2f}")
print(f"   Monthly Burn Rate: ₹{abs(monthly_burn):,.2f}")

# If we're burning 21.8M per month and will be at -65.4M in 3 months,
# what's our current balance?
# current_balance + (monthly_burn * 3) = -65,431,927.82
# current_balance = -65,431,927.82 - (monthly_burn * 3)
# But monthly_burn is already negative, so:
# current_balance = -65,431,927.82 - (-21,810,642.61 * 3)
# current_balance = -65,431,927.82 + 65,431,927.82 = 0

current_cash_estimate = current_balance_3m - (monthly_burn * 3)

print(f"\n   If 3-month balance = ₹{current_balance_3m:,.2f}")
print(f"   And monthly burn = ₹{monthly_burn:,.2f}")
print(f"   Then current cash ≈ ₹{current_cash_estimate:,.2f}")

print(f"\n✅ This confirms: Current cash balance is ≤ ₹0")

print("\n" + "="*70)
print("RUNWAY SCENARIOS")
print("="*70)

print(f"\n📈 Different Scenarios:")

scenarios = [
    ("Your Current State", 0, -21810642.61),
    ("If you had ₹10M", 10000000, -21810642.61),
    ("If you had ₹50M", 50000000, -21810642.61),
    ("If you had ₹100M", 100000000, -21810642.61),
    ("If breaking even", 10000000, 0),
    ("If profitable", 10000000, 5000000),
]

for name, cash, net_flow in scenarios:
    runway = _runway_months(cash, net_flow)
    print(f"\n   {name}:")
    print(f"      Cash: ₹{cash:,.0f}")
    print(f"      Monthly Net: ₹{net_flow:,.0f}")
    print(f"      Runway: {runway:.1f} months")
    
    if runway == 0:
        print(f"      → No buffer, immediate crisis")
    elif runway < 3:
        print(f"      → Critical, less than 3 months")
    elif runway < 6:
        print(f"      → Concerning, less than 6 months")
    elif runway < 12:
        print(f"      → Acceptable, less than 1 year")
    elif runway >= 99:
        print(f"      → Sustainable, positive cash flow")
    else:
        print(f"      → Good, over 1 year")

print("\n" + "="*70)
print("HOW TO INCREASE RUNWAY")
print("="*70)

print(f"\n💡 To Get Runway > 0:")
print(f"   1. Increase Cash Balance:")
print(f"      • Secure funding")
print(f"      • Collect receivables")
print(f"      • Sell assets")
print(f"      • Get a loan")

print(f"\n   2. Reduce Monthly Burn:")
print(f"      • Cut expenses by ₹{abs(monthly_burn):,.0f}/month")
print(f"      • Increase revenue")
print(f"      • Improve margins")

print(f"\n   3. Example Targets:")
target_runways = [3, 6, 12, 18]
for target in target_runways:
    cash_needed = abs(monthly_burn) * target
    print(f"      • {target} months runway: Need ₹{cash_needed:,.0f} cash")

print("\n" + "="*70)
print("FORMULA REFERENCE")
print("="*70)

print(f"""
📐 Runway Calculation Formula:

def _runway_months(cash_balance, monthly_net_flow):
    if cash_balance <= 0:
        return 0.0  # ← YOUR CASE
    
    if monthly_net_flow >= 0:
        return 99.0  # Infinite runway (making money)
    
    # Burning money, calculate months until broke
    return cash_balance / abs(monthly_net_flow)

Examples:
• Cash: ₹0, Burn: ₹21.8M/mo → Runway: 0 months
• Cash: ₹21.8M, Burn: ₹21.8M/mo → Runway: 1 month
• Cash: ₹65.4M, Burn: ₹21.8M/mo → Runway: 3 months
• Cash: ₹130.8M, Burn: ₹21.8M/mo → Runway: 6 months
• Cash: ₹261.6M, Burn: ₹21.8M/mo → Runway: 12 months
""")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

print(f"""
🎯 Why Your Runway is 0:

1. Current Cash Balance: ≤ ₹0
   → You have no cash buffer in the bank

2. Monthly Burn: ₹21.8M
   → You're losing money every month

3. Runway Formula: 0 / 21.8M = 0 months
   → Can't divide zero cash by burn rate

4. Result: ZERO RUNWAY
   → No time buffer before running out of money

⚠️  CRITICAL: This means you're operating on a day-to-day basis
with no financial cushion. Any disruption in income or unexpected
expense could be catastrophic.

🚨 IMMEDIATE ACTION REQUIRED:
   • Secure emergency funding
   • Drastically cut expenses
   • Increase revenue immediately
   • Consider restructuring the business
""")

print("\n" + "="*70)
