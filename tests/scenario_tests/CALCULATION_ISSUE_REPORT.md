# Scenario Calculation Issue Report

**Date:** May 13, 2026  
**Issue:** Growth rates not being applied correctly  
**Severity:** 🔴 HIGH - Affects all scenario projections

---

## 🐛 Problem Summary

The scenario calculation is **mathematically correct** for Month 1, but **growth rates are NOT being applied** in subsequent months.

### Expected Behavior
- Month 1: Base income + one-time items
- Month 2: Month 1 recurring × (1 + growth_rate)
- Month 3: Month 2 × (1 + growth_rate)
- etc.

### Actual Behavior
- Month 1: Base income + one-time items ✅
- Month 2: Same as Month 1 recurring (NO GROWTH) ❌
- Month 3-12: Same as Month 2 (NO GROWTH) ❌

---

## 📊 Evidence

### Test Scenario
```json
{
  "name": "Q3 2026 Growth Plan",
  "assumptions": {
    "revenue_growth_pct": 0.15,  // 15% monthly growth
    "expense_change_pct": 0.1,   // 10% monthly growth
    "one_time_income": 800000.0,
    "one_time_expense": 25000000.0
  }
}
```

### Results Analysis

| Month | Income | Expected | Actual | Growth Applied? |
|-------|--------|----------|--------|-----------------|
| 1 | $1,055,069.93 | $1,055,069.93 | $1,055,069.93 | ✅ (includes one-time) |
| 2 | $255,069.93 | $293,330.42 | $255,069.93 | ❌ NO GROWTH |
| 3-12 | $255,069.93 | Growing... | $255,069.93 | ❌ NO GROWTH |

**Expected Month 2 Income:**
```
Recurring from Month 1: $255,069.93
× (1 + 0.15) = $293,330.42
```

**Actual Month 2 Income:**
```
$255,069.93 (same as Month 1 recurring)
```

**Difference:** $38,260.49 missing (15% growth not applied)

---

## 🔍 Root Cause Analysis

### Location
**File:** `backend/services/scenario_service.py`  
**Function:** `_project_scenario()`  
**Lines:** 238-240

### The Bug

```python
# Line 238 - CURRENT CODE (WRONG)
inc = avg_income * (1 + a.get("revenue_growth_pct", 0) / 100) + a.get("new_monthly_revenue", 0)
```

### The Problem

The code divides by 100, assuming the input is a percentage (e.g., 15 for 15%).

However, the **assumptions are stored as decimals** (0.15 for 15%).

**What happens:**
```python
# Input: revenue_growth_pct = 0.15 (15%)
# Code: 1 + 0.15 / 100 = 1 + 0.0015 = 1.0015
# Result: Only 0.15% growth instead of 15% growth!
```

### Why Month 1 Looks Correct

Month 1 appears correct because:
1. It includes the large one-time expense ($25M)
2. The tiny growth (0.15% instead of 15%) is negligible compared to the base
3. The one-time items mask the growth calculation error

### Why Months 2-12 Are Wrong

The growth is being applied, but it's **100x too small**:
- Expected: 15% growth = 1.15x multiplier
- Actual: 0.15% growth = 1.0015x multiplier
- Difference: **99.87% of growth is missing**

---

## 🔧 The Fix

### Option 1: Remove Division by 100 (Recommended)

Since assumptions are already decimals, just remove the `/100`:

```python
# BEFORE (WRONG)
inc = avg_income * (1 + a.get("revenue_growth_pct", 0) / 100) + a.get("new_monthly_revenue", 0)

# AFTER (CORRECT)
inc = avg_income * (1 + a.get("revenue_growth_pct", 0)) + a.get("new_monthly_revenue", 0)
```

### Option 2: Convert Assumptions to Percentages

Change how assumptions are stored (NOT recommended - breaks existing data):

```python
# Store as percentages instead of decimals
"revenue_growth_pct": 15.0  # instead of 0.15
```

### Recommended Fix

**Use Option 1** - Remove `/100` from the calculation.

This is the correct fix because:
1. ✅ Matches the schema definition (decimals, not percentages)
2. ✅ Doesn't break existing data
3. ✅ Consistent with other parts of the codebase
4. ✅ Simpler and clearer

---

## 📝 Required Changes

### File: `backend/services/scenario_service.py`

**Line 238:** Revenue growth
```python
# BEFORE
inc = avg_income * (1 + a.get("revenue_growth_pct", 0) / 100) + a.get("new_monthly_revenue", 0)

# AFTER
inc = avg_income * (1 + a.get("revenue_growth_pct", 0)) + a.get("new_monthly_revenue", 0)
```

**Line 241:** Pricing change
```python
# BEFORE
inc *= (1 + a.get("pricing_change_pct", 0) / 100)

# AFTER
inc *= (1 + a.get("pricing_change_pct", 0))
```

**Line 244:** Customer churn
```python
# BEFORE
churn_factor = 1 - a.get("customer_churn_pct", 0) / 100

# AFTER
churn_factor = 1 - a.get("customer_churn_pct", 0)
```

**Line 252:** Expense change
```python
# BEFORE
exp = avg_expense * (1 + a.get("expense_change_pct", 0) / 100) - a.get("removed_monthly_expense", 0)

# AFTER
exp = avg_expense * (1 + a.get("expense_change_pct", 0)) - a.get("removed_monthly_expense", 0)
```

**Line 267:** Tax rate
```python
# BEFORE
tax = net_before_tax * (tax_rate / 100)

# AFTER
tax = net_before_tax * tax_rate
```

---

## ✅ Verification

After applying the fix, the results should be:

| Month | Income | Expenses | Net Cash Flow |
|-------|--------|----------|---------------|
| 1 | $1,055,069.93 | $29,448,203.24 | -$28,393,133.31 |
| 2 | $293,330.42 | $4,893,023.56 | -$4,599,693.14 |
| 3 | $337,330.00 | $5,382,325.92 | -$5,044,995.92 |
| 4 | $387,929.50 | $5,920,558.51 | -$5,532,629.01 |
| ... | Growing... | Growing... | Improving... |

**Key Changes:**
- ✅ Month 2 income grows by 15%: $255K → $293K
- ✅ Month 2 expenses grow by 10%: $4.4M → $4.9M
- ✅ Each month shows compounding growth
- ✅ Cumulative loss still significant but more realistic

---

## 🧪 Test Cases

### Test 1: Positive Growth
```python
assumptions = {
    "revenue_growth_pct": 0.10,  # 10%
    "expense_change_pct": 0.05,  # 5%
}
# Month 2 income should be 10% higher than Month 1 recurring
```

### Test 2: Negative Growth (Recession)
```python
assumptions = {
    "revenue_growth_pct": -0.10,  # -10%
    "expense_change_pct": -0.05,  # -5%
}
# Month 2 income should be 10% lower than Month 1 recurring
```

### Test 3: Zero Growth
```python
assumptions = {
    "revenue_growth_pct": 0.0,  # 0%
    "expense_change_pct": 0.0,  # 0%
}
# Month 2 should equal Month 1 recurring (no change)
```

### Test 4: High Growth
```python
assumptions = {
    "revenue_growth_pct": 1.0,  # 100%
    "expense_change_pct": 0.5,  # 50%
}
# Month 2 income should be 2x Month 1 recurring
```

---

## 📊 Impact Assessment

### Severity: 🔴 HIGH

**Affected Features:**
- ✅ Scenario projections (all scenarios)
- ✅ Scenario comparisons
- ✅ Monte Carlo simulations
- ✅ Sensitivity analysis
- ✅ Dashboard forecasts (if using scenarios)

**Data Integrity:**
- ❌ All existing scenario results are incorrect
- ❌ Need to recompute all scenarios after fix
- ✅ Assumptions data is correct (stored as decimals)
- ✅ No data migration needed

**User Impact:**
- 🔴 HIGH: Users see flat projections instead of growth
- 🔴 HIGH: Business decisions based on wrong data
- 🔴 HIGH: Scenario comparisons meaningless
- 🟡 MEDIUM: Templates still work (just need recomputation)

---

## 🚀 Deployment Plan

### Step 1: Apply Code Fix
1. Update `backend/services/scenario_service.py`
2. Remove `/100` from all percentage calculations
3. Run unit tests
4. Verify calculations manually

### Step 2: Recompute Existing Scenarios
```python
# Script to recompute all scenarios
async def recompute_all_scenarios():
    scenarios = await db.execute(select(Scenario))
    for scenario in scenarios:
        avg_inc, avg_exp, cash = await _get_baseline_financials(db, scenario.workspace_id)
        scenario.result_json = {"monthly": _project_scenario(avg_inc, avg_exp, cash, scenario.assumptions_json)}
        scenario.computed_at = datetime.now(timezone.utc)
    await db.commit()
```

### Step 3: Notify Users
- Send email about calculation fix
- Explain that scenarios have been recomputed
- Highlight that assumptions are unchanged
- Provide before/after comparison

### Step 4: Add Tests
- Add unit tests for growth calculations
- Add integration tests for scenarios
- Add regression tests to prevent future issues

---

## 📚 Related Issues

### Similar Issues to Check

1. **Forecasting Service** - Check if it has the same bug
2. **Budget Calculations** - Verify percentage handling
3. **Tax Calculations** - Verify tax rate handling
4. **Alert Thresholds** - Verify percentage comparisons

### Prevention

1. **Add Type Hints**
   ```python
   def _project_scenario(
       avg_income: float,
       avg_expense: float,
       current_cash: float,
       assumptions: dict,  # All percentages as decimals (0.15 = 15%)
       months: int = 12
   ):
   ```

2. **Add Validation**
   ```python
   # Validate that percentages are decimals, not whole numbers
   if assumptions.get("revenue_growth_pct", 0) > 2.0:
       raise ValueError("revenue_growth_pct should be decimal (0.15), not percentage (15)")
   ```

3. **Add Documentation**
   ```python
   """
   Project cash flow for N months.
   
   Args:
       assumptions: Dict with percentage fields as DECIMALS:
           - revenue_growth_pct: 0.15 for 15% growth
           - expense_change_pct: 0.10 for 10% growth
           - customer_churn_pct: 0.03 for 3% churn
   """
   ```

---

## ✅ Conclusion

### Summary
- **Bug:** Growth rates divided by 100 when they're already decimals
- **Impact:** All scenario projections show flat growth (0.15% instead of 15%)
- **Fix:** Remove `/100` from 5 lines in `_project_scenario()`
- **Effort:** 5 minutes to fix, 1 hour to test and deploy

### Recommendation
**Fix immediately** - This is a critical bug affecting core functionality.

### Next Steps
1. ✅ Apply code fix
2. ✅ Run tests
3. ✅ Recompute existing scenarios
4. ✅ Deploy to production
5. ✅ Notify users

---

**Report Created:** May 13, 2026  
**Reported By:** AI CFO Testing Team  
**Priority:** 🔴 CRITICAL  
**Status:** Ready for Fix
