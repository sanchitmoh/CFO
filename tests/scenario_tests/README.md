# Scenario Tests

This folder contains scenario-based tests for the application.

## Test Files

- `test_scenario_api.py` - API scenario tests
- `test_scenario_quick.py` - Quick scenario tests
- `test_scenario_schemas.py` - Schema validation tests
- `test_scenarios_example.py` - Example scenario tests
- `test_scenarios_manual.py` - Manual scenario tests
- `verify_calculation.py` - Calculation verification utility

## Documentation

- `CALCULATION_ISSUE_REPORT.md` - Report on calculation issues
- `TEST_SUMMARY.md` - Summary of test results

## Running Tests

Run all scenario tests:
```bash
pytest tests/scenario_tests/ -v
```

Run specific test:
```bash
pytest tests/scenario_tests/test_scenario_api.py -v
```

Run quick tests only:
```bash
pytest tests/scenario_tests/test_scenario_quick.py -v
```

## Manual Testing

For manual scenario testing:
```bash
python tests/scenario_tests/test_scenarios_manual.py
```

## Verification

To verify calculations:
```bash
python tests/scenario_tests/verify_calculation.py
```
