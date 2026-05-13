"""
Regression tests for alert settings contract and channel delivery wiring.
"""
from unittest.mock import AsyncMock, patch

import pytest

from schemas import AlertSettingsOut, AlertSettingsUpdate
from services.alert_engine import (
    _dispatch_workspace_notifications,
    _revenue_drop_summary,
    _serialize_monthly_income,
)


def test_alert_settings_update_accepts_channel_fields():
    payload = AlertSettingsUpdate.model_validate(
        {
            "low_cash_threshold": 4200,
            "high_expense_threshold": 15000,
            "anomaly_sensitivity": 2.2,
            "email_enabled": True,
            "email_addresses": [" finance@example.com ", "ops@example.com"],
            "slack_enabled": True,
            "slack_webhook_url": "  https://hooks.slack.com/services/T000/B000/SECRET  ",
        }
    )

    dumped = payload.model_dump(exclude_unset=True)

    assert dumped["email_enabled"] is True
    assert dumped["email_addresses"] == ["finance@example.com", "ops@example.com"]
    assert dumped["slack_enabled"] is True
    assert dumped["slack_webhook_url"] == "https://hooks.slack.com/services/T000/B000/SECRET"


def test_alert_settings_out_exposes_channel_defaults():
    config = AlertSettingsOut()

    assert config.email_enabled is False
    assert config.email_addresses == []
    assert config.slack_enabled is False
    assert config.slack_webhook_url is None


def test_revenue_drop_summary_uses_latest_year_month_period():
    monthly_income = _serialize_monthly_income(
        [
            (2025, 11, 1000),
            (2025, 12, 1200),
            (2026, 1, 800),
            (2026, 2, 500),
        ]
    )

    result = _revenue_drop_summary(monthly_income)

    assert result == ("2026-02", 500.0, 1000.0)


@pytest.mark.anyio
async def test_dispatch_workspace_notifications_uses_email_and_workspace_slack():
    config = AlertSettingsOut(
        email_enabled=True,
        email_addresses=["finance@example.com"],
        slack_enabled=True,
        slack_webhook_url="https://hooks.slack.com/services/T000/B000/SECRET",
    )
    created_alerts = [
        {
            "title": "Low cash balance",
            "message": "Balance is below threshold.",
            "severity": "critical",
            "category": "cash",
        }
    ]

    with patch("services.alert_engine.email_service.send_alert_email", new=AsyncMock(return_value=True)) as email_mock, patch(
        "services.alert_engine.slack_service.send_alert",
        new=AsyncMock(return_value=True),
    ) as slack_mock:
        await _dispatch_workspace_notifications(config, created_alerts)

    email_mock.assert_awaited_once()
    slack_mock.assert_awaited_once()
    assert slack_mock.await_args.kwargs["webhook_url"] == config.slack_webhook_url
