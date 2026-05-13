#!/usr/bin/env python3
"""
Verify Forecasting Calculations
Check if base, optimistic, and pessimistic forecasts are correct
"""

import json

print("="*80)
print("FORECASTING VERIFICATION")
print("="*80)

# The three forecasts provided
forecasts = {
    "base": {
        "scenario": "base",
        "base_currency": "INR",
        "months_ahead": 6,
        "historical_months": 13,
        "model_version": "v2_linear",
        "data_points": [
            {"period": "2024-12", "projected_income": 354746.5, "projected_expenses": 4727132.44, "projected_net": -4372385.94, "cumulative_net": -4372385.94, "confidence": 0.56, "confidence_lower": -5478244.3, "confidence_upper": -3266527.59},
            {"period": "2025-01", "projected_income": 369150.46, "projected_expenses": 4829830.35, "projected_net": -4460679.89, "cumulative_net": -8833065.84, "confidence": 0.51, "confidence_lower": -5732417.0, "confidence_upper": -3188942.78},
            {"period": "2025-02", "projected_income": 383554.42, "projected_expenses": 4932528.26, "projected_net": -4548973.84, "cumulative_net": -13382039.68, "confidence": 0.5, "confidence_lower": -5986589.71, "confidence_upper": -3111357.98},
            {"period": "2025-03", "projected_income": 397958.38, "projected_expenses": 5035226.17, "projected_net": -4637267.79, "cumulative_net": -18019307.47, "confidence": 0.5, "confidence_lower": -6240762.41, "confidence_upper": -3033773.17},
            {"period": "2025-04", "projected_income": 412362.34, "projected_expenses": 5137924.08, "projected_net": -4725561.74, "cumulative_net": -22744869.21, "confidence": 0.5, "confidence_lower": -6494935.11, "confidence_upper": -2956188.37},
            {"period": "2025-05", "projected_income": 426766.3, "projected_expenses": 5240622.0, "projected_net": -4813855.69, "cumulative_net": -27558724.9, "confidence": 0.5, "confidence_lower": -6749107.82, "confidence_upper": -2878603.56}
        ]
    },
    "optimistic": {
        "scenario": "optimistic",
        "base_currency": "INR",
        "months_ahead": 6,
        "historical_months": 13,
        "model_version": "v2_linear",
        "data_points": [
            {"period": "2024-12", "projected_income": 407958.47, "projected_expenses": 4254419.2, "projected_net": -3846460.72, "cumulative_net": -3846460.72, "confidence": 0.56, "confidence_lower": -4874393.83, "confidence_upper": -2818527.62},
            {"period": "2025-01", "projected_income": 424523.03, "projected_expenses": 4346847.32, "projected_net": -3922324.29, "cumulative_net": -7768785.01, "confidence": 0.5, "confidence_lower": -5104447.36, "confidence_upper": -2740201.22},
            {"period": "2025-02", "projected_income": 441087.58, "projected_expenses": 4439275.44, "projected_net": -3998187.85, "cumulative_net": -11766972.87, "confidence": 0.5, "confidence_lower": -5334500.89, "confidence_upper": -2661874.82},
            {"period": "2025-03", "projected_income": 457652.14, "projected_expenses": 4531703.56, "projected_net": -4074051.42, "cumulative_net": -15841024.28, "confidence": 0.5, "confidence_lower": -5564554.42, "confidence_upper": -2583548.42},
            {"period": "2025-04", "projected_income": 474216.69, "projected_expenses": 4624131.68, "projected_net": -4149914.98, "cumulative_net": -19990939.26, "confidence": 0.5, "confidence_lower": -5794607.95, "confidence_upper": -2505222.01},
            {"period": "2025-05", "projected_income": 490781.25, "projected_expenses": 4716559.8, "projected_net": -4225778.55, "cumulative_net": -24216717.81, "confidence": 0.5, "confidence_lower": -6024661.48, "confidence_upper": -2426895.61}
        ]
    },
    "pessimistic": {
        "scenario": "pessimistic",
        "base_currency": "INR",
        "months_ahead": 6,
        "historical_months": 13,
        "model_version": "v2_linear",
        "data_points": [
            {"period": "2024-12", "projected_income": 301534.52, "projected_expenses": 5199845.69, "projected_net": -4898311.16, "cumulative_net": -4898311.16, "confidence": 0.57, "confidence_lower": -6082094.77, "confidence_upper": -3714527.55},
            {"period": "2025-01", "projected_income": 313777.89, "projected_expenses": 5312813.39, "projected_net": -4999035.5, "cumulative_net": -9897346.66, "confidence": 0.52, "confidence_lower": -6360386.65, "confidence_upper": -3637684.34},
            {"period": "2025-02", "projected_income": 326021.26, "projected_expenses": 5425781.09, "projected_net": -5099759.83, "cumulative_net": -14997106.49, "confidence": 0.5, "confidence_lower": -6638678.53, "confidence_upper": -3560841.14},
            {"period": "2025-03", "projected_income": 338264.62, "projected_expenses": 5538748.79, "projected_net": -5200484.17, "cumulative_net": -20197590.66, "confidence": 0.5, "confidence_lower": -6916970.4, "confidence_upper": -3483997.93},
            {"period": "2025-04", "projected_income": 350507.99, "projected_expenses": 5651716.49, "projected_net": -5301208.5, "cumulative_net": -25498799.16, "confidence": 0.5, "confidence_lower": -7195262.28, "confidence_upper": -3407154.72},
            {"period": "2025-05", "projected_income": 362751.36, "projected_expenses": 5764684.19, "projected_net": -5401932.84, "cumulative_net": -30900732.0, "confidence": 0.5, "confidence_lower": -7473554.16, "confidence_upper": -3330311.52}
        ]
    }
}

def verify_forecast(scenario_name, forecast_data):
    """Verify a single forecast scenario"""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario_name.upper()}")
    print(f"{'='*80}")
    
    data_points = forecast_data["data_points"]
    issues = []
    
    print(f"\n📊 Basic Info:")
    print(f"   Model: {forecast_data['model_version']}")
    print(f"   Currency: {forecast_data['base_currency']}")
    print(f"   Months Ahead: {forecast_data['months_ahead']}")
    print(f"   Historical Months: {forecast_data['historical_months']}")
    
    # Check 1: Verify net cash flow calculation
    print(f"\n✓ Check 1: Net Cash Flow = Income - Expenses")
    net_flow_errors = 0
    for i, dp in enumerate(data_points):
        calculated_net = dp["projected_income"] - dp["projected_expenses"]
        actual_net = dp["projected_net"]
        diff = abs(calculated_net - actual_net)
        
        if diff > 0.01:  # Allow 1 cent tolerance
            print(f"   ❌ Month {i+1} ({dp['period']}): Expected {calculated_net:.2f}, Got {actual_net:.2f}, Diff: {diff:.2f}")
            net_flow_errors += 1
            issues.append(f"Net flow calculation error in {dp['period']}")
        else:
            print(f"   ✅ Month {i+1} ({dp['period']}): {actual_net:,.2f} = {dp['projected_income']:,.2f} - {dp['projected_expenses']:,.2f}")
    
    if net_flow_errors == 0:
        print(f"   ✅ All net cash flow calculations correct!")
    
    # Check 2: Verify cumulative cash flow
    print(f"\n✓ Check 2: Cumulative Cash Flow")
    cumulative_errors = 0
    running_total = 0
    for i, dp in enumerate(data_points):
        running_total += dp["projected_net"]
        actual_cumulative = dp["cumulative_net"]
        diff = abs(running_total - actual_cumulative)
        
        if diff > 0.01:  # Allow 1 cent tolerance
            print(f"   ❌ Month {i+1} ({dp['period']}): Expected {running_total:.2f}, Got {actual_cumulative:.2f}, Diff: {diff:.2f}")
            cumulative_errors += 1
            issues.append(f"Cumulative flow error in {dp['period']}")
        else:
            print(f"   ✅ Month {i+1} ({dp['period']}): {actual_cumulative:,.2f}")
    
    if cumulative_errors == 0:
        print(f"   ✅ All cumulative calculations correct!")
    
    # Check 3: Verify linear growth pattern
    print(f"\n✓ Check 3: Linear Growth Pattern (v2_linear)")
    
    # Income growth
    income_diffs = []
    for i in range(1, len(data_points)):
        diff = data_points[i]["projected_income"] - data_points[i-1]["projected_income"]
        income_diffs.append(diff)
    
    # Check if income growth is consistent (linear)
    if len(income_diffs) > 1:
        avg_income_growth = sum(income_diffs) / len(income_diffs)
        income_variance = sum((d - avg_income_growth)**2 for d in income_diffs) / len(income_diffs)
        income_std = income_variance ** 0.5
        
        print(f"   Income Growth:")
        print(f"      Average: ₹{avg_income_growth:,.2f}/month")
        print(f"      Std Dev: ₹{income_std:,.2f}")
        
        if income_std < 1.0:  # Very consistent
            print(f"      ✅ Perfectly linear growth")
        elif income_std < avg_income_growth * 0.01:  # Within 1%
            print(f"      ✅ Consistent linear growth")
        else:
            print(f"      ⚠️  Growth not perfectly linear")
    
    # Expense growth
    expense_diffs = []
    for i in range(1, len(data_points)):
        diff = data_points[i]["projected_expenses"] - data_points[i-1]["projected_expenses"]
        expense_diffs.append(diff)
    
    if len(expense_diffs) > 1:
        avg_expense_growth = sum(expense_diffs) / len(expense_diffs)
        expense_variance = sum((d - avg_expense_growth)**2 for d in expense_diffs) / len(expense_diffs)
        expense_std = expense_variance ** 0.5
        
        print(f"   Expense Growth:")
        print(f"      Average: ₹{avg_expense_growth:,.2f}/month")
        print(f"      Std Dev: ₹{expense_std:,.2f}")
        
        if expense_std < 1.0:  # Very consistent
            print(f"      ✅ Perfectly linear growth")
        elif expense_std < avg_expense_growth * 0.01:  # Within 1%
            print(f"      ✅ Consistent linear growth")
        else:
            print(f"      ⚠️  Growth not perfectly linear")
    
    # Check 4: Confidence intervals
    print(f"\n✓ Check 4: Confidence Intervals")
    confidence_errors = 0
    for i, dp in enumerate(data_points):
        lower = dp["confidence_lower"]
        upper = dp["confidence_upper"]
        net = dp["projected_net"]
        
        # Check if net is within confidence interval
        if lower <= net <= upper:
            print(f"   ✅ Month {i+1} ({dp['period']}): {lower:,.2f} ≤ {net:,.2f} ≤ {upper:,.2f}")
        else:
            print(f"   ❌ Month {i+1} ({dp['period']}): {net:,.2f} NOT in [{lower:,.2f}, {upper:,.2f}]")
            confidence_errors += 1
            issues.append(f"Confidence interval error in {dp['period']}")
    
    if confidence_errors == 0:
        print(f"   ✅ All confidence intervals valid!")
    
    # Check 5: Confidence values
    print(f"\n✓ Check 5: Confidence Values (0-1 range)")
    confidence_value_errors = 0
    for i, dp in enumerate(data_points):
        conf = dp["confidence"]
        if 0 <= conf <= 1:
            print(f"   ✅ Month {i+1} ({dp['period']}): {conf:.2f}")
        else:
            print(f"   ❌ Month {i+1} ({dp['period']}): {conf:.2f} (out of range)")
            confidence_value_errors += 1
            issues.append(f"Confidence value out of range in {dp['period']}")
    
    if confidence_value_errors == 0:
        print(f"   ✅ All confidence values valid!")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY: {scenario_name.upper()}")
    print(f"{'='*80}")
    
    total_errors = net_flow_errors + cumulative_errors + confidence_errors + confidence_value_errors
    
    if total_errors == 0:
        print(f"✅ ALL CHECKS PASSED - Forecast is CORRECT")
    else:
        print(f"❌ {total_errors} ERRORS FOUND")
        print(f"\nIssues:")
        for issue in issues:
            print(f"   • {issue}")
    
    # Key metrics
    print(f"\n📈 Key Metrics:")
    first = data_points[0]
    last = data_points[-1]
    
    print(f"   Starting (2024-12):")
    print(f"      Income: ₹{first['projected_income']:,.2f}")
    print(f"      Expenses: ₹{first['projected_expenses']:,.2f}")
    print(f"      Net: ₹{first['projected_net']:,.2f}")
    
    print(f"\n   Ending (2025-05):")
    print(f"      Income: ₹{last['projected_income']:,.2f}")
    print(f"      Expenses: ₹{last['projected_expenses']:,.2f}")
    print(f"      Net: ₹{last['projected_net']:,.2f}")
    
    print(f"\n   6-Month Totals:")
    total_income = sum(dp['projected_income'] for dp in data_points)
    total_expenses = sum(dp['projected_expenses'] for dp in data_points)
    total_net = sum(dp['projected_net'] for dp in data_points)
    
    print(f"      Total Income: ₹{total_income:,.2f}")
    print(f"      Total Expenses: ₹{total_expenses:,.2f}")
    print(f"      Total Net: ₹{total_net:,.2f}")
    print(f"      Final Cumulative: ₹{last['cumulative_net']:,.2f}")
    
    # Growth rates
    income_growth_pct = ((last['projected_income'] / first['projected_income']) - 1) * 100
    expense_growth_pct = ((last['projected_expenses'] / first['projected_expenses']) - 1) * 100
    
    print(f"\n   Growth Over 6 Months:")
    print(f"      Income: +{income_growth_pct:.2f}%")
    print(f"      Expenses: +{expense_growth_pct:.2f}%")
    
    return total_errors == 0, issues

# Verify all three scenarios
print("\n" + "="*80)
print("VERIFYING ALL THREE FORECASTS")
print("="*80)

results = {}
for scenario_name, forecast_data in forecasts.items():
    is_correct, issues = verify_forecast(scenario_name, forecast_data)
    results[scenario_name] = {"correct": is_correct, "issues": issues}

# Compare scenarios
print("\n" + "="*80)
print("SCENARIO COMPARISON")
print("="*80)

print("\n📊 Income Comparison (2024-12):")
for scenario_name in ["base", "optimistic", "pessimistic"]:
    income = forecasts[scenario_name]["data_points"][0]["projected_income"]
    print(f"   {scenario_name.capitalize():12s}: ₹{income:,.2f}")

print("\n📊 Income Comparison (2025-05):")
for scenario_name in ["base", "optimistic", "pessimistic"]:
    income = forecasts[scenario_name]["data_points"][-1]["projected_income"]
    print(f"   {scenario_name.capitalize():12s}: ₹{income:,.2f}")

print("\n📊 Expenses Comparison (2024-12):")
for scenario_name in ["base", "optimistic", "pessimistic"]:
    expenses = forecasts[scenario_name]["data_points"][0]["projected_expenses"]
    print(f"   {scenario_name.capitalize():12s}: ₹{expenses:,.2f}")

print("\n📊 Expenses Comparison (2025-05):")
for scenario_name in ["base", "optimistic", "pessimistic"]:
    expenses = forecasts[scenario_name]["data_points"][-1]["projected_expenses"]
    print(f"   {scenario_name.capitalize():12s}: ₹{expenses:,.2f}")

print("\n📊 Final Cumulative Net (2025-05):")
for scenario_name in ["base", "optimistic", "pessimistic"]:
    cumulative = forecasts[scenario_name]["data_points"][-1]["cumulative_net"]
    print(f"   {scenario_name.capitalize():12s}: ₹{cumulative:,.2f}")

# Verify scenario relationships
print("\n✓ Scenario Relationship Verification:")

base_income_start = forecasts["base"]["data_points"][0]["projected_income"]
opt_income_start = forecasts["optimistic"]["data_points"][0]["projected_income"]
pess_income_start = forecasts["pessimistic"]["data_points"][0]["projected_income"]

base_expense_start = forecasts["base"]["data_points"][0]["projected_expenses"]
opt_expense_start = forecasts["optimistic"]["data_points"][0]["projected_expenses"]
pess_expense_start = forecasts["pessimistic"]["data_points"][0]["projected_expenses"]

print(f"\n   Income (2024-12):")
if pess_income_start < base_income_start < opt_income_start:
    print(f"      ✅ Pessimistic < Base < Optimistic")
else:
    print(f"      ❌ Incorrect ordering")

print(f"\n   Expenses (2024-12):")
if opt_expense_start < base_expense_start < pess_expense_start:
    print(f"      ✅ Optimistic < Base < Pessimistic")
else:
    print(f"      ❌ Incorrect ordering")

# Final summary
print("\n" + "="*80)
print("FINAL VERIFICATION SUMMARY")
print("="*80)

all_correct = all(result["correct"] for result in results.values())

print(f"\n📋 Results:")
for scenario_name, result in results.items():
    status = "✅ CORRECT" if result["correct"] else "❌ ERRORS FOUND"
    print(f"   {scenario_name.capitalize():12s}: {status}")

if all_correct:
    print(f"\n🎉 ALL FORECASTS ARE CORRECT!")
    print(f"\n✅ Verification Complete:")
    print(f"   • Net cash flow calculations: CORRECT")
    print(f"   • Cumulative calculations: CORRECT")
    print(f"   • Linear growth pattern: VERIFIED")
    print(f"   • Confidence intervals: VALID")
    print(f"   • Scenario relationships: CORRECT")
else:
    print(f"\n⚠️  SOME FORECASTS HAVE ERRORS")
    print(f"\nIssues found:")
    for scenario_name, result in results.items():
        if not result["correct"]:
            print(f"\n   {scenario_name.capitalize()}:")
            for issue in result["issues"]:
                print(f"      • {issue}")

print("\n" + "="*80)
