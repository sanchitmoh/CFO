# Backend Tests

This folder contains all test files for the backend application.

## Test Categories

### Unit Tests
- `test_auth.py` - Authentication tests
- `test_password_policy.py` - Password policy unit tests
- `test_security.py` - Security tests
- `test_tax_calculation_service.py` - Tax calculation service tests

### Integration Tests
- `test_comprehensive_integration.py` - Comprehensive integration tests
- `test_password_policy_integration.py` - Password policy integration tests
- `test_phase25_scenarios_vendors.py` - Phase 2.5 scenarios and vendors tests
- `test_layer2_rls_remediation.py` - Row-level security remediation tests

### Scenario Tests
- `test_scenarios_example.py` - Example scenario tests
- `test_scenarios_manual.py` - Manual scenario tests

### Property-Based Tests
- `test_bug_condition_exploration.py` - Bug condition exploration with Hypothesis
- `test_preservation_properties.py` - Property preservation tests

### Service Tests
- `test_redis.py` - Redis service tests
- `test_redis_with_circuit_breaker.py` - Redis circuit breaker tests
- `test_vendor_sync.py` - Vendor synchronization tests

## Running Tests

Run all tests:
```bash
pytest backend/tests/
```

Run specific test file:
```bash
pytest backend/tests/test_auth.py -v
```

Run with coverage:
```bash
pytest backend/tests/ --cov=backend --cov-report=html
```

## Test Configuration

Test configuration is managed in `conftest.py`.

## Documentation

- `COMPREHENSIVE_TEST_AUDIT_REPORT.md` - Comprehensive test audit report
- `TEST_AUDIT_SUMMARY.md` - Test audit summary
- `FAILING_TESTS_DETAILS.md` - Details on failing tests
- `TEST_RESULTS_CHART.md` - Test results visualization
- `bug_condition_counterexamples.md` - Bug condition counterexamples
- `checkpoint_task5_summary.md` - Task 5 checkpoint summary
- `integration_test_coverage_report.md` - Integration test coverage report
