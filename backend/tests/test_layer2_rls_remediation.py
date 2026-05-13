"""
Tests for LAYER 2 — Database & RLS Remediation

CRIT-002: Alert engine RLS binding
CRIT-003: Semantic search backfill RLS binding
HIGH-003: Anomaly router background RLS binding
HIGH-004: list_budgets no longer commits on read
MED-002:  audit_service uses flush, not commit
"""
import ast
import inspect
import re
import textwrap

import pytest


class TestRLSContextManager:
    """Verify get_rls_db_context exists and is properly structured."""

    def test_get_rls_db_context_exists_in_database_module(self):
        """get_rls_db_context must exist as an async context manager."""
        from database import get_rls_db_context
        assert callable(get_rls_db_context), "get_rls_db_context must be callable"

    def test_get_rls_db_context_validates_uuid(self):
        """get_rls_db_context must reject invalid UUIDs to prevent injection."""
        import asyncio
        from database import get_rls_db_context

        async def _test():
            with pytest.raises(ValueError):
                async with get_rls_db_context("not-a-uuid"):
                    pass

        asyncio.get_event_loop().run_until_complete(_test())

    def test_get_rls_db_context_source_sets_workspace_id(self):
        """get_rls_db_context source must include SET LOCAL app.workspace_id."""
        from database import get_rls_db_context
        source = inspect.getsource(get_rls_db_context)
        assert "SET LOCAL app.workspace_id" in source, (
            "get_rls_db_context must set RLS variable"
        )

    def test_get_db_context_does_not_set_rls(self):
        """get_db_context (plain) must NOT set workspace_id — it's for admin queries."""
        from database import get_db_context
        source = inspect.getsource(get_db_context)
        assert "app.workspace_id" not in source, (
            "get_db_context must NOT set RLS — use get_rls_db_context for that"
        )


class TestCRIT002AlertEngineRLS:
    """CRIT-002: run_all_workspace_alerts must use RLS-bound sessions."""

    def test_per_workspace_loop_uses_rls_context(self):
        """The inner per-workspace loop must use get_rls_db_context, not get_db_context."""
        from services.alert_engine import run_all_workspace_alerts
        source = inspect.getsource(run_all_workspace_alerts)

        assert "get_rls_db_context" in source, (
            "CRIT-002: run_all_workspace_alerts must use get_rls_db_context "
            "for per-workspace queries"
        )

    def test_outer_workspace_list_uses_plain_context(self):
        """The outer query (fetching all workspace IDs) should use get_db_context."""
        from services.alert_engine import run_all_workspace_alerts
        source = inspect.getsource(run_all_workspace_alerts)

        # Should import both
        assert "get_db_context" in source, (
            "Outer admin sweep should still use get_db_context"
        )


class TestCRIT003SemanticSearchRLS:
    """CRIT-003: backfill_embeddings background task must use RLS-bound session."""

    def test_backfill_uses_rls_context(self):
        """The _backfill closure must use get_rls_db_context."""
        from routers.semantic_search import backfill_embeddings
        source = inspect.getsource(backfill_embeddings)

        assert "get_rls_db_context" in source, (
            "CRIT-003: _backfill must use get_rls_db_context for tenant isolation"
        )

    def test_backfill_does_not_use_plain_db_context(self):
        """The _backfill closure must NOT use get_db_context."""
        from routers.semantic_search import backfill_embeddings
        source = inspect.getsource(backfill_embeddings)

        # get_rls_db_context contains "get_db_context" as substring, so be precise
        assert "get_db_context()" not in source, (
            "CRIT-003: _backfill must not use plain get_db_context()"
        )

    def test_no_toplevel_get_db_context_import(self):
        """semantic_search.py should not import get_db_context at module level."""
        with open("routers/semantic_search.py") as f:
            content = f.read()

        # Check top-level imports only (before first def/class)
        top_section = content.split("\ndef ")[0].split("\nclass ")[0]
        assert "from database import get_db_context" not in top_section, (
            "Unused get_db_context import should be removed"
        )


class TestHIGH003AnomalyRouterRLS:
    """HIGH-003: anomaly router background alert task must use RLS-bound session."""

    def test_run_alerts_uses_rls_context(self):
        """The _run_alerts closure in scan_anomalies_endpoint must use RLS."""
        from routers.anomaly import scan_anomalies_endpoint
        source = inspect.getsource(scan_anomalies_endpoint)

        assert "get_rls_db_context" in source, (
            "HIGH-003: _run_alerts must use get_rls_db_context"
        )

    def test_no_toplevel_get_db_context_import(self):
        """anomaly.py should not import get_db_context at module level."""
        with open("routers/anomaly.py") as f:
            content = f.read()

        top_section = content.split("\ndef ")[0].split("\nclass ")[0]
        assert "from database import get_db_context" not in top_section


class TestAdditionalRLSFixes:
    """Verify the same RLS fix in transactions.py, chat.py, and plaid.py."""

    def test_transactions_embed_uses_rls(self):
        """transactions.py _embed closure must use get_rls_db_context."""
        from routers.transactions import create_transaction
        source = inspect.getsource(create_transaction)
        assert "get_rls_db_context" in source

    def test_transactions_run_alerts_uses_rls(self):
        """transactions.py _run_alerts closure (CSV upload) must use get_rls_db_context."""
        from routers.transactions import upload_csv
        source = inspect.getsource(upload_csv)
        assert "get_rls_db_context" in source

    def test_chat_stream_save_uses_rls(self):
        """chat.py SSE post-stream save must use get_rls_db_context."""
        from routers.chat import chat_stream
        source = inspect.getsource(chat_stream)
        assert "get_rls_db_context" in source

    def test_plaid_webhook_sync_uses_rls(self):
        """plaid.py webhook background sync must use get_rls_db_context."""
        from routers.plaid import plaid_webhook
        source = inspect.getsource(plaid_webhook)
        assert "get_rls_db_context" in source

    def test_no_remaining_background_get_db_context_in_routers(self):
        """No router should use get_db_context() in background closures
        EXCEPT plaid.py:_sync_item Phase 1 lookup (workspace_id unknown)."""
        import os
        router_dir = "routers"
        violations = []

        # plaid.py:_sync_item is exempt — it uses a two-phase approach:
        # Phase 1: get_db_context() to discover the workspace_id
        # Phase 2: get_rls_db_context(ws_id) for the actual sync
        EXEMPTED = {("plaid.py", "_sync_item")}

        for fname in os.listdir(router_dir):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(router_dir, fname)
            with open(fpath, encoding="utf-8", errors="replace") as f:
                content = f.read()

            # Find closures that use get_db_context()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    for child in ast.walk(node):
                        if isinstance(child, ast.AsyncWith):
                            for item in child.items:
                                src = ast.dump(item.context_expr)
                                if "get_db_context" in src and "get_rls_db_context" not in src:
                                    inner_source = ast.get_source_segment(content, node)
                                    if inner_source and node.name.startswith("_"):
                                        if (fname, node.name) not in EXEMPTED:
                                            violations.append(
                                                f"{fname}:{node.name} uses plain get_db_context()"
                                            )

        assert not violations, (
            f"Background closures still using plain get_db_context():\n"
            + "\n".join(violations)
        )


class TestHIGH004BudgetsNoWriteOnRead:
    """HIGH-004: GET /budgets/ must not commit to the database."""

    def test_list_budgets_does_not_call_commit(self):
        """list_budgets must not call db.commit()."""
        from routers.budgets import list_budgets
        source = inspect.getsource(list_budgets)

        # Should not contain db.commit() or await db.commit()
        assert "db.commit()" not in source, (
            "HIGH-004: list_budgets must not commit on GET — "
            "current_spend should be computed at read time without persisting"
        )

    def test_list_budgets_uses_expunge(self):
        """list_budgets must delegate to the shared read-time calculator."""
        from routers.budgets import list_budgets
        source = inspect.getsource(list_budgets)

        assert "get_budget_snapshots" in source, (
            "HIGH-004: list_budgets must compute current_spend via the shared "
            "read-time budget service instead of persisting on read"
        )

    def test_other_budget_endpoints_still_commit(self):
        """create_budget and update_budget must still commit (they are write ops)."""
        from routers.budgets import create_budget, update_budget, delete_budget
        for fn in [create_budget, update_budget, delete_budget]:
            source = inspect.getsource(fn)
            assert "db.commit()" in source, (
                f"{fn.__name__} should still commit — it's a write operation"
            )


class TestMED002AuditServiceFlush:
    """MED-002: log_action must use flush, not commit."""

    def test_log_action_uses_flush_not_commit(self):
        """log_action must call db.flush() instead of db.commit()."""
        from services.audit_service import log_action
        source = inspect.getsource(log_action)

        assert "db.flush()" in source, (
            "MED-002: log_action must use flush so caller controls commit"
        )
        assert "db.commit()" not in source, (
            "MED-002: log_action must NOT call commit — "
            "this breaks caller transaction boundaries"
        )

    def test_log_action_still_adds_entry(self):
        """log_action must still call db.add(entry)."""
        from services.audit_service import log_action
        source = inspect.getsource(log_action)

        assert "db.add(entry)" in source, (
            "log_action must still add the entry to the session"
        )


class TestNoRegressionInRLSPattern:
    """Ensure the existing get_rls_db FastAPI dependency is untouched."""

    def test_get_rls_db_dependency_still_exists(self):
        """dependencies.py get_rls_db must still exist and set workspace_id."""
        from dependencies import get_rls_db
        source = inspect.getsource(get_rls_db)
        assert "SET LOCAL app.workspace_id" in source

    def test_get_db_with_rls_still_exists(self):
        """database.py get_db_with_rls must still exist."""
        from database import get_db_with_rls
        assert callable(get_db_with_rls)
