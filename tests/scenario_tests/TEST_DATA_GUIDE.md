# Scenario Test Data Guide

**Comprehensive test data for scenario planning feature**

---

## 📊 Overview

This guide provides **20 realistic test scenarios** plus **5 edge cases** for comprehensive scenario testing. Each scenario includes:
- Revenue growth rate
- Expense change rate
- One-time income
- One-time expense
- Expected behavior description

---

## 🚀 Quick Start

### List All Scenarios
```bash
python use_test_data.py list
```

### View Specific Scenario
```bash
python use_test_data.py show test_001
```

### Generate cURL Command
```bash
python use_test_data.py curl test_003
```

### Compare Scenarios
```bash
python use_test_data.py compare test_001 test_002 test_010
```

---

## 📁 Test Scenarios by Category

### BASELINE (4 scenarios)
**Purpose:** Test normal, steady-state operations

| ID | Name | Revenue Growth | Expense Change | One-Time Items |
|----|------|----------------|----------------|----------------|
| test_001 | Steady Growth - Balanced | 10% | 8% | None |
| test_006 | Zero Growth - Status Quo | 0% | 0% | None |
| test_012 | Break-Even Push | 12% | 12% | None |
| test_014 | Minimal Growth | 2% | 1% | None |

**Use Cases:**
- Baseline comparisons
- Steady-state projections
- Conservative planning

---

### GROWTH (2 scenarios)
**Purpose:** Test high-growth scenarios

| ID | Name | Revenue Growth | Expense Change | One-Time Items |
|----|------|----------------|----------------|----------------|
| test_002 | High Growth - Aggressive | 20% | 15% | None |
| test_010 | Viral Growth | 50% | 30% | None |

**Use Cases:**
- Rapid expansion planning
- Hockey stick projections
- Scaling scenarios

---

### FUNDING (2 scenarios)
**Purpose:** Test external funding scenarios

| ID | Name | Revenue Growth | Expense Change | One-Time Income |
|----|------|----------------|----------------|-----------------|
| test_003 | Funding Round | 15% | 20% | $5,000,000 |
| test_008 | Small Business Grant | 5% | 5% | $50,000 |

**Use Cases:**
- Series A/B/C planning
- Grant applications
- Investment scenarios

---

### INVESTMENT (2 scenarios)
**Purpose:** Test capital expenditure scenarios

| ID | Name | Revenue Growth | Expense Change | One-Time Expense |
|----|------|----------------|----------------|------------------|
| test_004 | Major Investment | 10% | 8% | $2,000,000 |
| test_009 | Office Renovation | 8% | 8% | $500,000 |

**Use Cases:**
- Equipment purchases
- Facility upgrades
- Infrastructure investments

---

### ACQUISITION (1 scenario)
**Purpose:** Test M&A scenarios

| ID | Name | Revenue Growth | Expense Change | One-Time Items |
|----|------|----------------|----------------|----------------|
| test_005 | Acquisition Scenario | 15% | 10% | +$10M / -$8M |

**Use Cases:**
- Company acquisitions
- Asset purchases
- Strategic investments

---

### FINANCIAL (2 scenarios)
**Purpose:** Test financial restructuring

| ID | Name | Revenue Growth | Expense Change | One-Time Items |
|----|------|----------------|----------------|----------------|
| test_013 | Debt Payoff | 8% | 6% | +$3M / -$2.5M |
| test_015 | Asset Sale | 5% | 5% | +$750K |

**Use Cases:**
- Debt management
- Asset liquidation
- Financial optimization

---

### RECESSION (1 scenario)
**Purpose:** Test downturn scenarios

| ID | Name | Revenue Growth | Expense Change | One-Time Items |
|----|------|----------------|----------------|----------------|
| test_007 | Recession Scenario | -10% | -15% | None |

**Use Cases:**
- Economic downturn planning
- Cost-cutting scenarios
- Survival strategies

---

### TURNAROUND (1 scenario)
**Purpose:** Test recovery scenarios

| ID | Name | Revenue Growth | Expense Change | One-Time Items |
|----|------|----------------|----------------|----------------|
| test_018 | Turnaround Strategy | -5% | -20% | None |

**Use Cases:**
- Business recovery
- Restructuring plans
- Margin improvement

---

### STARTUP (1 scenario)
**Purpose:** Test early-stage scenarios

| ID | Name | Revenue Growth | Expense Change | One-Time Items |
|----|------|----------------|----------------|----------------|
| test_011 | Seed + Product Launch | 25% | 20% | +$1M / -$300K |

**Use Cases:**
- Seed funding
- Product launches
- Early-stage growth

---

### IPO (1 scenario)
**Purpose:** Test IPO preparation

| ID | Name | Revenue Growth | Expense Change | One-Time Items |
|----|------|----------------|----------------|----------------|
| test_019 | IPO Preparation | 18% | 15% | +$50M / -$5M |

**Use Cases:**
- IPO planning
- Late-stage funding
- Public company preparation

---

### BOOTSTRAP (1 scenario)
**Purpose:** Test organic growth

| ID | Name | Revenue Growth | Expense Change | One-Time Items |
|----|------|----------------|----------------|----------------|
| test_020 | Bootstrapped Growth | 15% | 10% | None |

**Use Cases:**
- Self-funded growth
- Organic expansion
- Sustainable scaling

---

### RISK (1 scenario)
**Purpose:** Test risk scenarios

| ID | Name | Revenue Growth | Expense Change | One-Time Expense |
|----|------|----------------|----------------|------------------|
| test_016 | Legal Settlement | 10% | 8% | $1,500,000 |

**Use Cases:**
- Legal risks
- Unexpected expenses
- Contingency planning

---

### RECOVERY (1 scenario)
**Purpose:** Test recovery scenarios

| ID | Name | Revenue Growth | Expense Change | One-Time Items |
|----|------|----------------|----------------|----------------|
| test_017 | Insurance Payout + Rebuild | 8% | 8% | +$2M / -$1.8M |

**Use Cases:**
- Disaster recovery
- Insurance claims
- Rebuilding scenarios

---

## 🔬 Edge Cases

### Purpose
Test extreme values and boundary conditions

| ID | Name | Description |
|----|------|-------------|
| edge_001 | Extreme Positive Growth | 100% revenue, 50% expense growth |
| edge_002 | Extreme Negative Growth | -50% revenue and expense decline |
| edge_003 | Massive One-Time Income | $100M funding |
| edge_004 | Massive One-Time Expense | $100M acquisition |
| edge_005 | Both Massive One-Time Items | $100M funding, $90M expense |

**Use Cases:**
- Boundary testing
- System limits
- Error handling

---

## 📋 Usage Examples

### Example 1: Create a Funding Scenario

```bash
# View the scenario
python use_test_data.py show test_003

# Generate cURL command
python use_test_data.py curl test_003

# Execute (replace YOUR_TOKEN)
curl -X POST http://localhost:8000/api/scenarios \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Funding Round",
    "description": "Large one-time income (Series A funding)",
    "assumptions": {
      "revenue_growth_pct": 0.15,
      "expense_change_pct": 0.2,
      "one_time_income": 5000000.0,
      "one_time_expense": 0.0
    }
  }'
```

### Example 2: Compare Growth Scenarios

```bash
# Compare baseline, high growth, and viral growth
python use_test_data.py compare test_001 test_002 test_010
```

Output:
```
Metric                        test_001       test_002       test_010
----------------------------------------------------------------------
Revenue Growth %                  10.0%          20.0%          50.0%
Expense Change %                   8.0%          15.0%          30.0%
One-time Income              $        0     $        0     $        0
One-time Expense             $        0     $        0     $        0
```

### Example 3: Test All Scenarios Programmatically

```python
import json

# Load test data
with open('test_data.json', 'r') as f:
    data = json.load(f)

# Test each scenario
for scenario in data['test_scenarios']:
    print(f"Testing: {scenario['name']}")
    
    # Create scenario via API
    response = create_scenario(scenario['assumptions'])
    
    # Verify results
    assert response['status'] == 'success'
    print(f"✅ {scenario['id']} passed")
```

---

## 🎯 Testing Strategy

### 1. Smoke Tests (Quick)
Test a few key scenarios to verify basic functionality:
- test_001 (Baseline)
- test_003 (Funding)
- test_004 (Investment)

### 2. Comprehensive Tests (Full)
Test all 20 scenarios to verify all features:
- All baseline scenarios
- All growth scenarios
- All funding scenarios
- All edge cases

### 3. Regression Tests (Automated)
Run all scenarios after code changes:
```bash
for scenario in test_001 test_002 test_003 ... test_020; do
    python use_test_data.py curl $scenario | bash
done
```

---

## 📊 Expected Results

### Baseline Scenarios
- **Steady growth** in revenue and expenses
- **Predictable** cash flow patterns
- **No surprises** in Month 1

### Growth Scenarios
- **Accelerating** revenue
- **Improving** margins over time
- **Compounding** effects visible

### Funding Scenarios
- **Large positive** cash flow in Month 1
- **Return to normal** in Month 2+
- **Growth trajectory** maintained

### Investment Scenarios
- **Large negative** cash flow in Month 1
- **Recovery** in subsequent months
- **Long-term benefit** from investment

### Recession Scenarios
- **Declining** revenue
- **Faster cost cutting** than revenue decline
- **Improving margins** despite lower revenue

---

## 🔍 Validation Rules

### Revenue Growth
- **Min:** -99% (near-total collapse)
- **Max:** 1000% (10x growth)
- **Typical:** -20% to +50%

### Expense Change
- **Min:** -99% (near-total elimination)
- **Max:** 1000% (10x increase)
- **Typical:** -30% to +40%

### One-Time Income
- **Min:** $0
- **Max:** $1B
- **Typical:** $0 to $10M

### One-Time Expense
- **Min:** $0
- **Max:** $1B
- **Typical:** $0 to $10M

---

## 🛠️ Customization

### Create Custom Scenario

```python
custom_scenario = {
    "id": "custom_001",
    "name": "My Custom Scenario",
    "description": "Custom test case",
    "category": "custom",
    "assumptions": {
        "revenue_growth_pct": 0.12,
        "expense_change_pct": 0.10,
        "one_time_income": 100000.0,
        "one_time_expense": 50000.0,
        # ... other assumptions
    },
    "expected_behavior": "What you expect to happen"
}
```

### Add to Test Data

```python
# Load existing data
with open('test_data.json', 'r') as f:
    data = json.load(f)

# Add custom scenario
data['test_scenarios'].append(custom_scenario)

# Save
with open('test_data.json', 'w') as f:
    json.dump(data, f, indent=2)
```

---

## 📈 Performance Benchmarks

### Expected Performance
- **Scenario creation:** < 500ms
- **Calculation time:** < 100ms
- **API response:** < 1s

### Load Testing
Use test data for load testing:
```bash
# Create 100 scenarios concurrently
for i in {1..100}; do
    python use_test_data.py curl test_001 | bash &
done
wait
```

---

## 🐛 Troubleshooting

### Issue: Scenario creation fails
**Solution:** Check that assumptions are within valid ranges

### Issue: Growth rates not applied
**Solution:** Verify the bug fix has been applied (remove `/100`)

### Issue: One-time items not showing
**Solution:** Check Month 1 results specifically

### Issue: Cumulative cash flow incorrect
**Solution:** Verify net cash flow calculations

---

## 📚 Related Documentation

- [SCENARIO_TESTING_GUIDE.md](../../docs/SCENARIO_TESTING_GUIDE.md)
- [SCENARIO_QUICK_REFERENCE.md](../../docs/SCENARIO_QUICK_REFERENCE.md)
- [CALCULATION_ISSUE_REPORT.md](./CALCULATION_ISSUE_REPORT.md)
- [README.md](./README.md)

---

## ✅ Checklist

### Before Testing
- [ ] Backend server running
- [ ] Database migrated
- [ ] JWT token obtained
- [ ] Test data loaded

### During Testing
- [ ] Test baseline scenarios
- [ ] Test growth scenarios
- [ ] Test funding scenarios
- [ ] Test edge cases
- [ ] Verify calculations
- [ ] Check error handling

### After Testing
- [ ] Document results
- [ ] Report bugs
- [ ] Update test data
- [ ] Share findings

---

**Test Data Version:** 1.0.0  
**Last Updated:** May 13, 2026  
**Total Scenarios:** 25 (20 standard + 5 edge cases)  
**Status:** ✅ Ready for Use
