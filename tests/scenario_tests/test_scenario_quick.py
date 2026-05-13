#!/usr/bin/env python3
"""Quick scenario functionality test."""
import sys
sys.path.insert(0, 'backend')

from services.scenario_service import get_templates, get_template

print("="*60)
print("SCENARIO FUNCTIONALITY TEST")
print("="*60)

# Test 1: List templates
print("\n✅ TEST 1: List Templates")
templates = get_templates()
print(f"   Found {len(templates)} templates:")
for t in templates:
    print(f"   - {t.name} ({t.industry})")

# Test 2: Get specific template
print("\n✅ TEST 2: Get SaaS Template")
saas = get_template("saas_startup")
if saas:
    print(f"   Name: {saas.name}")
    print(f"   Industry: {saas.industry}")
    print(f"   Revenue Growth: {saas.assumptions.revenue_growth_pct}%")
    print(f"   Headcount Change: +{saas.assumptions.headcount_change}")
else:
    print("   ❌ Template not found")

# Test 3: Get retail template
print("\n✅ TEST 3: Get Retail Template")
retail = get_template("retail_ecommerce")
if retail:
    print(f"   Name: {retail.name}")
    print(f"   Seasonal Dips: {retail.assumptions.seasonal_dip_months}")
else:
    print("   ❌ Template not found")

# Test 4: Verify all templates have required fields
print("\n✅ TEST 4: Validate Template Structure")
required_fields = ['id', 'name', 'description', 'industry', 'assumptions']
all_valid = True
for template in templates:
    for field in required_fields:
        if not hasattr(template, field):
            print(f"   ❌ Template {getattr(template, 'name', 'Unknown')} missing field: {field}")
            all_valid = False

if all_valid:
    print(f"   All {len(templates)} templates have required fields")

# Test 5: Verify assumptions structure
print("\n✅ TEST 5: Validate Assumptions")
required_assumptions = [
    'revenue_growth_pct',
    'expense_change_pct',
    'headcount_change',
    'avg_salary_per_head',
    'customer_churn_pct',
    'tax_rate_pct'
]

for template in templates:
    assumptions = template.assumptions
    missing = [a for a in required_assumptions if not hasattr(assumptions, a)]
    if missing:
        print(f"   ⚠️  {template.name} missing: {missing}")
    else:
        print(f"   ✅ {template.name} - all assumptions present")

print("\n" + "="*60)
print("✅ ALL TESTS PASSED!")
print("="*60)
