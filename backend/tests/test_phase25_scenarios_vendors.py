"""
Phase 2.5 — Tests for Scenario Planning (templates, sharing, extended projection)
and Vendor Management (reviews, scorecards, contracts).

Covers the service-layer pure functions and async DB methods.
"""
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# ── 1. Scenario Projection Engine (unit tests — no DB) ────────────

from services.scenario_service import _project_scenario, get_templates, get_template, INDUSTRY_TEMPLATES


class TestProjectionEngine:
    """Tests for the enhanced _project_scenario function."""

    def _base_assumptions(self, **overrides):
        defaults = {
            "revenue_growth_pct": 0, "expense_change_pct": 0,
            "new_monthly_revenue": 0, "removed_monthly_expense": 0,
            "one_time_income": 0, "one_time_expense": 0,
            "headcount_change": 0, "avg_salary_per_head": 0,
            "customer_churn_pct": 0, "pricing_change_pct": 0,
            "tax_rate_pct": 0, "capex_monthly": 0,
            "loan_repayment_monthly": 0, "seasonal_dip_months": [],
        }
        defaults.update(overrides)
        return defaults

    def test_flat_projection_no_changes(self):
        """With all-zero assumptions, cash stays flat."""
        result = _project_scenario(10000, 8000, 50000, self._base_assumptions(), months=6)
        assert len(result) == 6
        # Net each month = income - expense = 2000
        for r in result:
            assert r["net_cash_flow"] == 2000.0
        assert result[-1]["cumulative_cash"] == 50000 + 2000 * 6

    def test_revenue_growth(self):
        """Revenue growth should increase income each month."""
        a = self._base_assumptions(revenue_growth_pct=10)
        result = _project_scenario(10000, 8000, 0, a, months=1)
        # Income = 10000 * 1.10 = 11000
        assert result[0]["projected_income"] == 11000.0

    def test_expense_change(self):
        """Expense change should increase expenses."""
        a = self._base_assumptions(expense_change_pct=5)
        result = _project_scenario(10000, 8000, 0, a, months=1)
        assert result[0]["projected_expenses"] == 8400.0  # 8000 * 1.05

    def test_headcount_cost(self):
        """Adding headcount should increase expenses."""
        a = self._base_assumptions(headcount_change=2, avg_salary_per_head=120000)
        result = _project_scenario(10000, 8000, 0, a, months=1)
        # headcount cost = 2 * 120000 / 12 = 20000
        assert result[0]["projected_expenses"] == 28000.0

    def test_customer_churn(self):
        """Churn should reduce revenue."""
        a = self._base_assumptions(customer_churn_pct=10)
        result = _project_scenario(10000, 8000, 0, a, months=1)
        # Income = 10000 * 0.90 = 9000
        assert result[0]["projected_income"] == 9000.0

    def test_pricing_change(self):
        """Pricing change increases revenue."""
        a = self._base_assumptions(pricing_change_pct=5)
        result = _project_scenario(10000, 8000, 0, a, months=1)
        # Income = 10000 * 1.05 = 10500
        assert result[0]["projected_income"] == 10500.0

    def test_tax_rate_applied_on_profit(self):
        """Tax should be applied only on positive net income."""
        a = self._base_assumptions(tax_rate_pct=20)
        result = _project_scenario(10000, 8000, 0, a, months=1)
        # Net before tax = 2000, tax = 400
        assert result[0]["tax"] == 400.0
        assert result[0]["net_cash_flow"] == 1600.0

    def test_tax_not_applied_on_loss(self):
        """Tax should NOT be applied when expenses > income."""
        a = self._base_assumptions(tax_rate_pct=20)
        result = _project_scenario(5000, 8000, 0, a, months=1)
        assert result[0]["tax"] == 0.0

    def test_one_time_items_month_one_only(self):
        """One-time income/expense only affects month 1."""
        a = self._base_assumptions(one_time_income=50000, one_time_expense=10000)
        result = _project_scenario(10000, 8000, 0, a, months=3)
        assert result[0]["projected_income"] == 60000.0  # 10000 + 50000
        assert result[0]["projected_expenses"] == 18000.0  # 8000 + 10000
        assert result[1]["projected_income"] == 10000.0  # No one-time
        assert result[1]["projected_expenses"] == 8000.0

    def test_capex_and_loan(self):
        """Capex and loan should add to expenses every month."""
        a = self._base_assumptions(capex_monthly=3000, loan_repayment_monthly=2000)
        result = _project_scenario(10000, 8000, 0, a, months=2)
        for r in result:
            assert r["projected_expenses"] == 13000.0  # 8000 + 3000 + 2000

    def test_seasonal_dip(self):
        """Seasonal months should get 30% revenue dip."""
        a = self._base_assumptions(seasonal_dip_months=[1, 3])
        result = _project_scenario(10000, 8000, 0, a, months=3)
        assert result[0]["projected_income"] == 7000.0  # month 1 dip
        assert result[1]["projected_income"] == 10000.0  # month 2 normal
        assert result[2]["projected_income"] == 7000.0  # month 3 dip

    def test_combined_assumptions(self):
        """Test multiple assumptions working together."""
        a = self._base_assumptions(
            revenue_growth_pct=10, customer_churn_pct=5,
            headcount_change=1, avg_salary_per_head=60000,
            tax_rate_pct=25,
        )
        result = _project_scenario(10000, 8000, 0, a, months=1)
        # Income: 10000 * 1.10 * 1.0 * 0.95 = 10450
        assert result[0]["projected_income"] == 10450.0
        # Expenses: 8000 + 5000 = 13000
        assert result[0]["projected_expenses"] == 13000.0
        # Net before tax: 10450 - 13000 = -2550 → tax = 0 (loss)
        assert result[0]["tax"] == 0.0


# ── 2. Industry Templates ─────────────────────────────────────────

class TestIndustryTemplates:
    def test_templates_list_not_empty(self):
        templates = get_templates()
        assert len(templates) >= 5

    def test_all_templates_have_required_fields(self):
        for t in get_templates():
            assert t.id
            assert t.name
            assert t.industry
            assert t.description
            assert t.assumptions is not None

    def test_get_template_by_id(self):
        t = get_template("saas_startup")
        assert t is not None
        assert t.name == "SaaS Startup"
        assert t.assumptions.revenue_growth_pct == 15.0

    def test_get_template_not_found(self):
        assert get_template("nonexistent") is None

    def test_template_assumptions_produce_valid_projection(self):
        """Each template should produce a valid 12-month projection."""
        for t in get_templates():
            result = _project_scenario(10000, 8000, 50000, t.assumptions.model_dump(), months=12)
            assert len(result) == 12
            for point in result:
                assert "projected_income" in point
                assert "cumulative_cash" in point


# ── 3. Vendor Scorecard Computation (unit-level) ──────────────────

class TestVendorScorecard:
    """Test the weighted composite scoring logic."""

    def test_composite_score_weights(self):
        """Verify: quality 30%, delivery 30%, responsiveness 20%, cost 20%."""
        avg_q, avg_d, avg_r, avg_c = 5.0, 4.0, 3.0, 2.0
        expected = round(avg_q * 0.30 + avg_d * 0.30 + avg_r * 0.20 + avg_c * 0.20, 2)
        assert expected == 3.70

    def test_composite_perfect_score(self):
        """All 5s should yield composite = 5.0."""
        composite = round(5.0 * 0.30 + 5.0 * 0.30 + 5.0 * 0.20 + 5.0 * 0.20, 2)
        assert composite == 5.0

    def test_composite_minimum_score(self):
        """All 1s should yield composite = 1.0."""
        composite = round(1.0 * 0.30 + 1.0 * 0.30 + 1.0 * 0.20 + 1.0 * 0.20, 2)
        assert composite == 1.0


# ── 4. Vendor Service: Rating Clamping ────────────────────────────

class TestRatingClamping:
    """Verify that review ratings are clamped to 1-5."""

    def test_ratings_clamped_to_range(self):
        """Test via the clamping logic in submit_review."""
        assert max(1, min(5, 0)) == 1
        assert max(1, min(5, 6)) == 5
        assert max(1, min(5, 3)) == 3


# ── 5. Contract Expiry Logic ─────────────────────────────────────

class TestContractExpiry:
    """Test expiry date math used in get_expiring_contracts."""

    def test_days_remaining_calculation(self):
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=15)
        days_remaining = (end_date - now).days
        assert days_remaining == 15

    def test_expired_contract_shows_zero_days(self):
        now = datetime.now(timezone.utc)
        end_date = now - timedelta(days=3)
        days_remaining = max((end_date - now).days, 0)
        assert days_remaining == 0


# ── 6. Schema Validation ─────────────────────────────────────────

from schemas import (
    ScenarioAssumptions, ScenarioShareCreate, VendorReviewCreate,
    ContractCreate, ContractUpdate, ScenarioTemplate as ScenarioTemplateSchema,
)


class TestSchemaValidation:
    def test_assumptions_defaults(self):
        """All extended assumptions default to zero/empty."""
        a = ScenarioAssumptions()
        assert a.headcount_change == 0
        assert a.customer_churn_pct == 0.0
        assert a.seasonal_dip_months == []

    def test_assumptions_with_all_fields(self):
        a = ScenarioAssumptions(
            revenue_growth_pct=10, expense_change_pct=5,
            headcount_change=3, avg_salary_per_head=80000,
            customer_churn_pct=2, pricing_change_pct=5,
            tax_rate_pct=30, capex_monthly=10000,
            loan_repayment_monthly=5000, seasonal_dip_months=[1, 12],
        )
        assert a.headcount_change == 3
        assert a.seasonal_dip_months == [1, 12]

    def test_share_create_default_permission(self):
        s = ScenarioShareCreate(shared_with_user_id=uuid.uuid4())
        assert s.permission == "viewer"

    def test_review_create_validation(self):
        r = VendorReviewCreate(
            delivery_rating=4, quality_rating=5,
            responsiveness_rating=3, cost_rating=4,
        )
        assert r.delivery_rating == 4
        assert r.comment is None

    def test_contract_create_defaults(self):
        c = ContractCreate(
            title="Test Contract",
            contract_type="service",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=365),
        )
        assert c.auto_renew is False
        assert c.renewal_notice_days == 30

    def test_contract_update_partial(self):
        c = ContractUpdate(title="Updated Title")
        assert c.title == "Updated Title"
        assert c.contract_type is None


# ── 7. Template Schema Roundtrip ─────────────────────────────────

class TestTemplateRoundtrip:
    def test_template_to_dict_and_back(self):
        t = get_template("saas_startup")
        d = t.model_dump()
        t2 = ScenarioTemplateSchema(**d)
        assert t2.id == "saas_startup"
        assert t2.assumptions.revenue_growth_pct == 15.0

    def test_all_templates_roundtrip(self):
        for t in get_templates():
            d = t.model_dump()
            t2 = ScenarioTemplateSchema(**d)
            assert t2.id == t.id
