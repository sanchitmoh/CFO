# Runway Calculation Explanation

## Why is Runway 0 Months?

### Quick Answer
**Your current cash balance is ≤ ₹0**, which means you have no financial buffer. The runway calculation returns 0 when there's no cash in the bank.

---

## Understanding Runway

### Formula
```
Runway (months) = Current Cash Balance / Monthly Burn Rate
```

### Logic
```python
def _runway_months(cash_balance, monthly_net_flow):
    # Case 1: No cash left
    if cash_balance <= 0:
        return 0.0  # ← YOUR SITUATION
    
    # Case 2: Making money (positive cash flow)
    if monthly_net_flow >= 0:
        return 99.0  # Infinite runway
    
    # Case 3: Burning cash (negative cash flow)
    return cash_balance / abs(monthly_net_flow)
```

---

## Your Financial Situation

### Current State
- **Current Cash Balance**: ≤ ₹0
- **Monthly Burn Rate**: ₹21,810,642.61
- **3-Month Projected Balance**: ₹-65,431,927.82
- **Runway**: **0.0 months**

### What This Means
- ❌ No cash buffer in the bank
- ❌ Already at or below ₹0
- ❌ Can't survive even 1 month without new income
- ⚠️ Operating on a day-to-day basis with no cushion

---

## Runway Scenarios

| Scenario | Cash Balance | Monthly Net Flow | Runway | Status |
|----------|--------------|------------------|--------|--------|
| **Your Current State** | ₹0 | ₹-21.8M | **0.0 months** | 🚨 Immediate crisis |
| If you had ₹10M | ₹10M | ₹-21.8M | 0.5 months | 🔴 Critical |
| If you had ₹50M | ₹50M | ₹-21.8M | 2.3 months | 🔴 Critical |
| If you had ₹100M | ₹100M | ₹-21.8M | 4.6 months | 🟡 Concerning |
| If breaking even | ₹10M | ₹0 | 99.0 months | ✅ Sustainable |
| If profitable | ₹10M | ₹+5M | 99.0 months | ✅ Sustainable |

---

## How to Increase Runway

### Option 1: Increase Cash Balance
- Secure funding (investors, loans)
- Collect outstanding receivables
- Sell non-essential assets
- Get a line of credit

### Option 2: Reduce Monthly Burn
- Cut expenses by ₹21.8M/month
- Increase revenue
- Improve profit margins
- Reduce headcount or salaries

### Target Runway Goals

| Target Runway | Cash Needed |
|---------------|-------------|
| 3 months | ₹65,431,928 |
| 6 months | ₹130,863,856 |
| 12 months | ₹261,727,711 |
| 18 months | ₹392,591,567 |

---

## Calculation Breakdown

### Working Backwards
```
3-Month Projected Balance: ₹-65,431,927.82
Monthly Burn Rate: ₹-21,810,642.61

Current Cash = 3-Month Balance - (Monthly Burn × 3)
Current Cash = -65,431,927.82 - (-21,810,642.61 × 3)
Current Cash = -65,431,927.82 + 65,431,927.82
Current Cash ≈ ₹0
```

This confirms: **Current cash balance is ≤ ₹0**

---

## Examples

### Runway with Different Cash Levels
```
• Cash: ₹0, Burn: ₹21.8M/mo → Runway: 0 months
• Cash: ₹21.8M, Burn: ₹21.8M/mo → Runway: 1 month
• Cash: ₹65.4M, Burn: ₹21.8M/mo → Runway: 3 months
• Cash: ₹130.8M, Burn: ₹21.8M/mo → Runway: 6 months
• Cash: ₹261.6M, Burn: ₹21.8M/mo → Runway: 12 months
```

---

## Summary

### Why Runway is 0

1. **Current Cash Balance**: ≤ ₹0
   - You have no cash buffer in the bank

2. **Monthly Burn**: ₹21.8M
   - You're losing money every month

3. **Runway Formula**: 0 / 21.8M = 0 months
   - Can't divide zero cash by burn rate

4. **Result**: ZERO RUNWAY
   - No time buffer before running out of money

### Critical Warning

⚠️ **This means you're operating on a day-to-day basis with no financial cushion.** Any disruption in income or unexpected expense could be catastrophic.

### Immediate Action Required

🚨 **URGENT STEPS:**
1. Secure emergency funding
2. Drastically cut expenses
3. Increase revenue immediately
4. Consider restructuring the business

---

## Related Files

- **Affordability Calculator**: `backend/services/calculator_service.py`
- **Verification Script**: `tests/scenario_tests/verify_affordability.py`
- **Explanation Script**: `tests/scenario_tests/explain_runway_calculation.py`

---

## Conclusion

The runway calculation is **working correctly**. The 0-month runway accurately reflects your financial situation: **you have no cash buffer**. This is not a bug—it's a critical warning that immediate action is needed to secure the business's financial stability.
