import asyncio
import sys
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from models import TransactionType
from services import chat_service, embedding_service


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)


class _FakeDb:
    def __init__(self, rows):
        self.rows = rows
        self.execute_calls = 0

    async def execute(self, _query):
        self.execute_calls += 1
        return _FakeResult(self.rows)


def test_balance_and_burn_rate_share_transaction_totals_query():
    db = _FakeDb([
        (TransactionType.income, 1200, 2),
        (TransactionType.expense, 900, 3),
    ])
    cache = {}
    cutoff = datetime.now(timezone.utc)
    workspace_id = uuid.uuid4()

    async def run():
        balance_text, balance_meta = await chat_service._fetch_balance(
            db, workspace_id, cutoff, "$", cache
        )
        burn_text, burn_meta = await chat_service._fetch_burn_rate(
            db, workspace_id, cutoff, "$", cache
        )
        return balance_text, balance_meta, burn_text, burn_meta

    balance_text, balance_meta, burn_text, burn_meta = asyncio.run(run())

    assert db.execute_calls == 1
    assert balance_meta["txn_count"] == 5
    assert "Total Income (last 90 days): $1,200.00" in balance_text
    assert burn_meta["burn_rate"] == pytest.approx(300.0)
    assert "Monthly Burn Rate (last 90 days): $300.00" in burn_text


def test_embedding_model_loads_from_local_cache_only(monkeypatch):
    calls = {}

    class FakeSentenceTransformer:
        def __init__(self, model_name, **kwargs):
            calls["model_name"] = model_name
            calls["kwargs"] = kwargs

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=FakeSentenceTransformer),
    )
    monkeypatch.setattr(embedding_service, "_model", None)
    monkeypatch.setattr(embedding_service, "_model_unavailable", False)

    model = embedding_service._get_model()

    assert model is not None
    assert calls["model_name"] == embedding_service.settings.EMBEDDING_MODEL
    assert calls["kwargs"]["local_files_only"] is True


@pytest.mark.anyio
async def test_semantic_search_skips_model_load_on_request_path(monkeypatch):
    class GuardDb:
        async def execute(self, _query):
            raise AssertionError("semantic search should not hit the database")

    monkeypatch.setattr(embedding_service, "_model", None)
    monkeypatch.setattr(embedding_service, "_model_unavailable", False)

    rows = await embedding_service.get_relevant_transactions(
        GuardDb(),
        workspace_id=uuid.uuid4(),
        query="cash runway",
        top_k=5,
    )

    assert rows == []
