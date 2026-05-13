"""
Regression tests for affordability calculations.
"""
from schemas import AffordabilityRequest
from services.calculator_service import _calculate_affordability_response


def make_request(**overrides) -> AffordabilityRequest:
    payload = {
        "expense_name": "New laptop",
        "amount": 1000.0,
        "frequency": "one_time",
        "is_hire": False,
    }
    payload.update(overrides)
    return AffordabilityRequest(**payload)


def test_one_time_expense_reduces_cash_not_monthly_burn():
    response = _calculate_affordability_response(
        current_cash_balance=10000.0,
        income_3m=9000.0,
        expense_3m=12000.0,
        req=make_request(amount=3000.0, frequency="one_time"),
        sym="$",
    )

    assert response.can_afford is True
    assert response.current_runway_months == 10.0
    assert response.projected_runway_months == 7.0
    assert response.current_balance_3m == 7000.0
    assert response.projected_balance_3m == 4000.0
    assert response.break_even_revenue is None


def test_monthly_expense_changes_projected_burn_and_cash():
    response = _calculate_affordability_response(
        current_cash_balance=10000.0,
        income_3m=9000.0,
        expense_3m=12000.0,
        req=make_request(amount=2000.0, frequency="monthly"),
        sym="$",
    )

    assert response.can_afford is True
    assert response.current_runway_months == 10.0
    assert response.projected_runway_months == 3.3
    assert response.current_balance_3m == 7000.0
    assert response.projected_balance_3m == 1000.0


def test_negative_cash_does_not_report_negative_runway():
    response = _calculate_affordability_response(
        current_cash_balance=-5000.0,
        income_3m=6000.0,
        expense_3m=9000.0,
        req=make_request(amount=500.0, frequency="one_time"),
        sym="$",
    )

    assert response.can_afford is False
    assert response.current_runway_months == 0.0
    assert response.projected_runway_months == 0.0
    assert response.current_balance_3m == -8000.0
    assert response.projected_balance_3m == -8500.0
    assert response.break_even_revenue == 8500.0


def test_break_even_revenue_matches_projected_cash_gap():
    response = _calculate_affordability_response(
        current_cash_balance=5000.0,
        income_3m=3000.0,
        expense_3m=6000.0,
        req=make_request(amount=2000.0, frequency="monthly", is_hire=True, expense_name="Sales hire"),
        sym="$",
    )

    assert response.can_afford is False
    assert response.projected_runway_months == 1.7
    assert response.projected_balance_3m == -4000.0
    assert response.break_even_revenue == 4000.0
    assert "this hire" in response.ai_suggestion


def test_annual_expense_is_treated_as_recurring_not_upfront():
    response = _calculate_affordability_response(
        current_cash_balance=12000.0,
        income_3m=9000.0,
        expense_3m=12000.0,
        req=make_request(amount=2400.0, frequency="annual"),
        sym="$",
    )

    assert response.can_afford is True
    assert response.current_runway_months == 12.0
    assert response.projected_runway_months == 10.0
    assert response.current_balance_3m == 9000.0
    assert response.projected_balance_3m == 8400.0
