"""
Regression tests for forecasting math.
"""
from services.forecast_service import (
    _compute_forecast,
    _linear_fit,
    _residual_stddev,
)


def test_linear_forecast_uses_fit_intercept_for_simple_trend():
    monthly_data = {
        "2024-01": {"income": 100.0, "expenses": 50.0},
        "2024-02": {"income": 200.0, "expenses": 60.0},
        "2024-03": {"income": 300.0, "expenses": 70.0},
    }

    forecast = _compute_forecast(monthly_data, months_ahead=1, scenario="base")

    assert len(forecast) == 1
    assert forecast[0].period == "2024-04"
    assert forecast[0].projected_income == 400.0
    assert forecast[0].projected_expenses == 80.0
    assert forecast[0].projected_net == 320.0
    assert forecast[0].cumulative_net == 320.0


def test_confidence_band_reflects_expense_volatility():
    monthly_data = {
        "2024-01": {"income": 100.0, "expenses": 70.0},
        "2024-02": {"income": 200.0, "expenses": 130.0},
        "2024-03": {"income": 300.0, "expenses": 110.0},
    }

    forecast = _compute_forecast(monthly_data, months_ahead=1, scenario="base")
    point = forecast[0]

    expense_values = [monthly_data[period]["expenses"] for period in sorted(monthly_data)]
    expense_intercept, expense_slope = _linear_fit(expense_values)
    expense_std = _residual_stddev(expense_values, expense_intercept, expense_slope)
    projected_expense = expense_intercept + expense_slope * len(expense_values)
    projected_income = 400.0
    projected_net = projected_income - projected_expense

    assert expense_std > 0
    assert point.projected_net == round(projected_net, 2)
    assert point.confidence_lower == round(projected_net - expense_std, 2)
    assert point.confidence_upper == round(projected_net + expense_std, 2)
    assert point.confidence_lower < point.projected_net < point.confidence_upper


def test_scenario_multiplier_applies_to_projected_values():
    monthly_data = {
        "2024-01": {"income": 100.0, "expenses": 50.0},
        "2024-02": {"income": 200.0, "expenses": 60.0},
        "2024-03": {"income": 300.0, "expenses": 70.0},
    }

    base = _compute_forecast(monthly_data, months_ahead=1, scenario="base")[0]
    optimistic = _compute_forecast(monthly_data, months_ahead=1, scenario="optimistic")[0]
    pessimistic = _compute_forecast(monthly_data, months_ahead=1, scenario="pessimistic")[0]

    assert optimistic.projected_income == 460.0
    assert optimistic.projected_expenses == 72.0
    assert optimistic.projected_net > base.projected_net

    assert pessimistic.projected_income == 340.0
    assert pessimistic.projected_expenses == 88.0
    assert pessimistic.projected_net < base.projected_net
