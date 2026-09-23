"""ADVANCE-004: Enable Row-Level Security on critical tenant-scoped tables.

Phase 1 (critical): transactions, budgets, alerts, chat_sessions, chat_messages
Phase 2 (security hardening): users, goals, alert_rules, forecast_results, audit_logs, file_uploads, plaid_items

Revision ID: 001_enable_rls
Revises:
Create Date: 2026-04-19
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "001_enable_rls"
down_revision = "000_baseline_schema"
branch_labels = None
depends_on = None

# ── All tenant-scoped tables requiring RLS ─────────────────────────
CRITICAL_TABLES = [
    "transactions",
    "budgets",
    "alerts",
    "chat_sessions",
    "chat_messages",
    # SEC-FIX: Add missing tables to prevent cross-tenant data access
    "users",
    "goals",
    "alert_rules",
    "forecast_results",
    "audit_logs",
    "file_uploads",
    "plaid_items",
]


def upgrade() -> None:
    """Enable RLS and create workspace isolation policies on critical tables.

    Each policy ensures queries only see rows belonging to the workspace set
    via `SET LOCAL app.workspace_id = '<uuid>'` at session start.

    The Alembic migration runner itself runs as a superuser and is not
    affected by RLS (superusers bypass RLS by default in PostgreSQL).
    """
    for table in CRITICAL_TABLES:
        op.execute(f"""
            DO $$ BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = '{table}'
                ) THEN
                    ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
                    DROP POLICY IF EXISTS workspace_isolation_{table} ON {table};
                    CREATE POLICY workspace_isolation_{table}
                    ON {table}
                    USING (workspace_id = current_setting('app.workspace_id', true)::UUID)
                    WITH CHECK (workspace_id = current_setting('app.workspace_id', true)::UUID);
                END IF;
            END $$;
        """)

    # NOTE: We use current_setting('app.workspace_id', true) with the
    # `true` flag so it returns NULL (and thus blocks all rows) if the
    # setting is not set, rather than raising an error. This is safer
    # than failing open.


def downgrade() -> None:
    """Disable RLS and drop policies."""
    for table in reversed(CRITICAL_TABLES):
        op.execute(f"""
            DO $$ BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = '{table}'
                ) THEN
                    DROP POLICY IF EXISTS workspace_isolation_{table} ON {table};
                    ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
                END IF;
            END $$;
        """)
