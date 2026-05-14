from datetime import datetime, timezone
from types import SimpleNamespace

from routers.dashboard import _build_investor_payload
from schemas import CategoryAmount, DashboardSummary, HealthScoreResponse, ScoreComponent


def test_investor_payload_uses_historical_window_and_real_health_score():
    summary = DashboardSummary(
        total_income=1_350_000,
        total_expenses=900_000,
        net_cash_flow=450_000,
        transaction_count=87,
        burn_rate=150_000,
        runway_months=3.0,
        budget_utilization=82.4,
        active_alerts=1,
        cash_balance=450_000,
        monthly_income=[120_000, 180_000, 210_000, 240_000, 270_000, 330_000],
        monthly_expenses=[110_000, 140_000, 145_000, 155_000, 165_000, 185_000],
        monthly_periods=["2024-06", "2024-07", "2024-08", "2024-09", "2024-10", "2024-11"],
        top_categories=[
            CategoryAmount(category="Payroll", amount=300_000),
            CategoryAmount(category="Marketing", amount=200_000),
        ],
        recent_transactions=[],
        period_months=6,
    )
    workspace = SimpleNamespace(name="Northstar Foods", industry="food_and_beverage", currency="INR")
    health = HealthScoreResponse(
        overall_score=67,
        grade="B",
        stage="growth",
        components=[
            ScoreComponent(
                name="Cash Flow",
                score=13,
                max_score=20,
                description="Positive but thin cash flow (weight: 20%)",
                status="good",
            )
        ],
        recommendations=["Increase revenue or reduce expenses to improve cash flow"],
        computed_at=datetime(2026, 5, 14, tzinfo=timezone.utc),
    )

    payload = _build_investor_payload(
        summary=summary,
        workspace=workspace,
        health=health,
        latest_date=datetime(2024, 11, 27, tzinfo=timezone.utc),
        earliest_date=datetime(2024, 3, 1, tzinfo=timezone.utc),
        cogs_total=180_000,
        now=datetime(2026, 5, 14, tzinfo=timezone.utc),
    )

    assert payload.company.name == "Northstar Foods"
    assert payload.company.industry == "Food And Beverage"
    assert payload.health_score == 67
    assert payload.data_quality.historical is True
    assert payload.data_quality.window_start.date().isoformat() == "2024-05-31"
    assert payload.revenue_trend[-1].period == "2024-11"
    assert payload.metrics[0].label == "Revenue in Window"
    assert payload.kpis[0].label == "Gross Margin"
    assert payload.kpis[0].value == "86.7%"
    assert payload.expense_mix[0].category == "Payroll"
    assert payload.expense_mix[0].share_pct == 33.3
    assert "historical" in payload.narrative.lower()
    assert any("recent transactions" in item.lower() for item in payload.recommendations)
