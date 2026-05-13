"""
Regression tests for anomaly detection scanning behavior.
"""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from models import TransactionType
from services.anomaly_service import _anchored_cutoff, scan_anomalies, scan_anomalies_stream


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self._values


class _SingleValueResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeDb:
    def __init__(self, transactions, workspace):
        self.transactions = transactions
        self.workspace = workspace
        self.executed_sql: list[str] = []
        self.commit = AsyncMock()

    async def get(self, model, workspace_id):
        return self.workspace

    async def execute(self, statement):
        sql = str(statement)
        self.executed_sql.append(sql)
        if "transactions.is_anomaly IS NULL" in sql:
            return _ScalarResult([])
        return _ScalarResult(self.transactions)


def _make_transactions():
    base_date = datetime(2024, 11, 1, tzinfo=timezone.utc)
    return [
        SimpleNamespace(
            id=uuid.uuid4(),
            date=base_date + timedelta(days=index),
            description=f"Expense {index}",
            amount=150.0 + index,
            category="Operations",
            type=TransactionType.expense,
            account="Main Account",
            is_anomaly=False,
            anomaly_score=None,
        )
        for index in range(3)
    ]


@pytest.mark.anyio
async def test_anchored_cutoff_uses_latest_transaction_date():
    latest = datetime(2024, 11, 27, 18, 30, tzinfo=timezone.utc)

    class _CutoffDb:
        async def execute(self, statement):
            return _SingleValueResult(latest)

    cutoff = await _anchored_cutoff(_CutoffDb(), uuid.uuid4(), 365)

    assert cutoff == latest - timedelta(days=365)


@pytest.mark.anyio
async def test_scan_anomalies_rescores_full_window_with_cached_model():
    transactions = _make_transactions()
    db = _FakeDb(transactions, SimpleNamespace(currency="USD"))
    workspace_id = uuid.uuid4()
    cutoff = datetime(2023, 12, 1, tzinfo=timezone.utc)
    cached_stats = {
        "Operations": {"mean": 100.0, "std": 10.0, "count": 3, "cv": 0.1},
    }

    cache_get_mock = AsyncMock(return_value=cached_stats)

    with (
        patch("services.anomaly_service._anchored_cutoff", AsyncMock(return_value=cutoff)),
        patch("services.anomaly_service.calibrate_category_thresholds", AsyncMock(return_value={"__default__": 1.5, "Operations": 1.5})),
        patch("services.anomaly_service._should_rebuild_model", AsyncMock(return_value=(False, 3))),
        patch("services.anomaly_service.cache_get", cache_get_mock),
    ):
        result = await scan_anomalies(db, workspace_id, None, 365)

    assert result.scanned == 3
    assert result.anomalies_found == 3
    assert all(anomaly.category == "Operations" for anomaly in result.anomalies)
    assert all("transactions.is_anomaly IS NULL" not in sql for sql in db.executed_sql)
    assert any(call.args and call.args[0].endswith(":anomaly_stats:365") for call in cache_get_mock.await_args_list)
    db.commit.assert_awaited()


@pytest.mark.anyio
async def test_scan_anomalies_stream_rescores_full_window_with_cached_model():
    transactions = _make_transactions()
    db = _FakeDb(transactions, SimpleNamespace(currency="USD"))
    workspace_id = uuid.uuid4()
    cutoff = datetime(2023, 12, 1, tzinfo=timezone.utc)
    cached_stats = {
        "Operations": {"mean": 100.0, "std": 10.0, "count": 3, "cv": 0.1},
    }

    cache_get_mock = AsyncMock(return_value=cached_stats)

    with (
        patch("services.anomaly_service._anchored_cutoff", AsyncMock(return_value=cutoff)),
        patch("services.anomaly_service.calibrate_category_thresholds", AsyncMock(return_value={"__default__": 1.5, "Operations": 1.5})),
        patch("services.anomaly_service._should_rebuild_model", AsyncMock(return_value=(False, 3))),
        patch("services.anomaly_service.cache_get", cache_get_mock),
    ):
        events = [event async for event in scan_anomalies_stream(db, workspace_id, None, 365)]

    anomaly_events = [payload for event_type, payload in events if event_type == "anomaly"]
    done_events = [payload for event_type, payload in events if event_type == "done"]

    assert len(anomaly_events) == 3
    assert done_events == [{"scanned": 3, "anomalies_found": 3}]
    assert all("transactions.is_anomaly IS NULL" not in sql for sql in db.executed_sql)
    assert any(call.args and call.args[0].endswith(":anomaly_stats:365") for call in cache_get_mock.await_args_list)
    db.commit.assert_awaited()
