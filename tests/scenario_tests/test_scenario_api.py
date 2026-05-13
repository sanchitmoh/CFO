#!/usr/bin/env python3
"""Test scenario API endpoints."""
import requests
import json

BASE_URL = "http://localhost:8000"

print("="*60)
print("SCENARIO API ENDPOINT TESTS")
print("="*60)

# Test 1: Health check
print("\n✅ TEST 1: Health Check")
try:
    response = requests.get(f"{BASE_URL}/api/health")
    if response.status_code == 200:
        print(f"   Status: {response.json()['status']}")
        print(f"   Version: {response.json()['version']}")
    else:
        print(f"   ❌ Failed: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: List templates (no auth required for templates)
print("\n✅ TEST 2: List Scenario Templates")
try:
    # Note: This endpoint requires authentication in production
    # For testing, we'll try without auth first
    response = requests.get(f"{BASE_URL}/api/scenarios/templates")
    
    if response.status_code == 200:
        templates = response.json()
        print(f"   Found {len(templates)} templates:")
        for t in templates:
            print(f"   - {t['name']} ({t['industry']})")
    elif response.status_code == 401:
        print(f"   ⚠️  Authentication required (expected in production)")
        print(f"   Status: {response.status_code}")
    else:
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Get specific template
print("\n✅ TEST 3: Get SaaS Template")
try:
    response = requests.get(f"{BASE_URL}/api/scenarios/templates/saas_startup")
    
    if response.status_code == 200:
        template = response.json()
        print(f"   Name: {template['name']}")
        print(f"   Industry: {template['industry']}")
        print(f"   Revenue Growth: {template['assumptions']['revenue_growth_pct']}%")
    elif response.status_code == 401:
        print(f"   ⚠️  Authentication required")
    else:
        print(f"   Status: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Try to list scenarios (will require auth)
print("\n✅ TEST 4: List Scenarios (Auth Required)")
try:
    response = requests.get(f"{BASE_URL}/api/scenarios")
    
    if response.status_code == 200:
        scenarios = response.json()
        print(f"   Found {len(scenarios)} scenarios")
    elif response.status_code == 401:
        print(f"   ✅ Authentication required (expected)")
        print(f"   Message: Authentication needed to access scenarios")
    else:
        print(f"   Status: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 5: Check API documentation
print("\n✅ TEST 5: API Documentation Available")
try:
    response = requests.get(f"{BASE_URL}/docs")
    if response.status_code == 200:
        print(f"   ✅ Swagger docs available at {BASE_URL}/docs")
    else:
        print(f"   Status: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 6: Check OpenAPI schema
print("\n✅ TEST 6: OpenAPI Schema")
try:
    response = requests.get(f"{BASE_URL}/openapi.json")
    if response.status_code == 200:
        schema = response.json()
        
        # Check if scenario endpoints are documented
        paths = schema.get('paths', {})
        scenario_paths = [p for p in paths.keys() if '/scenarios' in p]
        
        print(f"   ✅ OpenAPI schema available")
        print(f"   Found {len(scenario_paths)} scenario endpoints:")
        for path in sorted(scenario_paths)[:5]:
            print(f"   - {path}")
        if len(scenario_paths) > 5:
            print(f"   ... and {len(scenario_paths) - 5} more")
    else:
        print(f"   Status: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "="*60)
print("✅ API TESTS COMPLETE")
print("="*60)
print("\nNOTE: Full scenario CRUD operations require authentication.")
print("To test authenticated endpoints:")
print("1. Login at http://localhost:3000")
print("2. Get JWT token from browser DevTools")
print("3. Use token in Authorization header")
print("\nExample:")
print('curl -H "Authorization: Bearer YOUR_TOKEN" \\')
print(f'  {BASE_URL}/api/scenarios')
