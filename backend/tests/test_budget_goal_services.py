"""
Regression tests for budget and goal shared services.
"""
import inspect
import uuid
from types import SimpleNamespace

from services import alert_engine, chat_service, dashboard_service, health_score_service
from services.budget_service import (
    build_budget_snapshot,
    normalize_category_key,
    normalize_category_label,
)
from services.goal_service import compute_goal_progress, is_goal_complete


def test_budget_snapshot_uses_threshold_aware_status():
    budget = SimpleNamespace(
        id=uuid.uuid4(),
        category=" Marketing ",
        monthly_limit=50000,
        alert_threshold=0.8,
        month="2026-05",
    )

    snapshot = build_budget_snapshot(budget, current_spend=42000)

    assert snapshot.category == "Marketing"
    assert snapshot.percentage_used == 84.0
    assert snapshot.status == "warning"


def test_budget_category_normalization_is_stable():
    assert normalize_category_label("  Marketing   Spend  ") == "Marketing Spend"
    assert normalize_category_key("  Marketing   Spend  ") == "marketing spend"


def test_expense_reduction_progress_inverts_the_ratio():
    assert compute_goal_progress("expense_reduction", current_value=32, target_value=28) == 87.5
    assert compute_goal_progress("expense_reduction", current_value=20, target_value=28) == 100.0


def test_expense_reduction_completion_requires_lower_current_value():
    assert not is_goal_complete("expense_reduction", current_value=32, target_value=28)
    assert is_goal_complete("expense_reduction", current_value=20, target_value=28)


def test_budget_consumers_use_shared_budget_service():
    for module in [dashboard_service, health_score_service, alert_engine, chat_service]:
        source = inspect.getsource(module)
        assert "Budget.current_spend" not in source
        assert "get_budget_" in source
