"""L-003: Baseline schema — creates all tables from SQLAlchemy models.

This is a "stamp" migration: existing databases already have these tables
(created via Base.metadata.create_all), so they should run:

    alembic stamp 000_baseline_schema

New databases will run this migration normally via `alembic upgrade head`.

Revision ID: 000_baseline_schema
Revises:
Create Date: 2026-04-26
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = "000_baseline_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all AI CFO tables in dependency order."""

    # ── Extensions ─────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")

    # ── workspaces ─────────────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("industry", sa.String(50), nullable=False, server_default="general_smb"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("fiscal_year_start", sa.SmallInteger, nullable=False, server_default="1"),
        sa.Column("is_demo", sa.Boolean, server_default="false"),
        sa.Column("alert_config", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_workspaces_industry", "workspaces", ["industry"])

    # ── users ──────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("clerk_id", sa.String(255), unique=True, nullable=True),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("owner", "admin", "cfo", "accountant", "investor", "employee", name="userrole", create_type=True), server_default="owner"),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_users_clerk_id", "users", ["clerk_id"])
    op.create_index("ix_users_workspace_id", "users", ["workspace_id"])
    op.create_index("idx_users_email_ws", "users", ["email", "workspace_id"], unique=True)

    # ── transactions ───────────────────────────────────────────────
    op.create_table(
        "transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("type", sa.Enum("income", "expense", name="transactiontype", create_type=True), nullable=False),
        sa.Column("account", sa.String(100), nullable=False, server_default="Main Account"),
        sa.Column("vendor", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_anomaly", sa.Boolean, server_default="false"),
        sa.Column("anomaly_score", sa.Float, nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.CheckConstraint("amount >= 0", name="ck_txn_amount_positive"),
    )
    op.create_index("ix_transactions_date", "transactions", ["date"])
    op.create_index("ix_transactions_category", "transactions", ["category"])
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("idx_txn_ws_date", "transactions", ["workspace_id", "date"])
    op.create_index("idx_txn_ws_cat_date", "transactions", ["workspace_id", "category", "date"])
    op.create_index("idx_txn_ws_type", "transactions", ["workspace_id", "type"])
    op.create_index("idx_txn_ws_type_cat_date", "transactions", ["workspace_id", "type", "category", "date"])

    # ── budgets ────────────────────────────────────────────────────
    op.create_table(
        "budgets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("monthly_limit", sa.Numeric(12, 2), nullable=False),
        sa.Column("alert_threshold", sa.Float, nullable=False, server_default="0.8"),
        sa.Column("current_spend", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_budgets_user_id", "budgets", ["user_id"])
    op.create_index("idx_budget_ws_cat_month", "budgets", ["workspace_id", "category", "month"], unique=True)

    # ── goals ──────────────────────────────────────────────────────
    op.create_table(
        "goals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("target_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("current_value", sa.Numeric(14, 2), server_default="0"),
        sa.Column("metric_type", sa.String(50), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Enum("active", "completed", "abandoned", name="goalstatus", create_type=True), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_goals_user_id", "goals", ["user_id"])
    op.create_index("idx_goals_ws_status", "goals", ["workspace_id", "status"])

    # ── alerts ─────────────────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("severity", sa.Enum("info", "warning", "critical", name="alertseverity", create_type=True), server_default="info"),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("action_url", sa.Text, nullable=True),
        sa.Column("is_read", sa.Boolean, server_default="false"),
        sa.Column("is_dismissed", sa.Boolean, server_default="false"),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])
    op.create_index("idx_alerts_ws_unread", "alerts", ["workspace_id", "is_read", "created_at"])

    # ── alert_rules ────────────────────────────────────────────────
    op.create_table(
        "alert_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("threshold_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("is_enabled", sa.Boolean, server_default="true"),
        sa.Column("notify_email", sa.Boolean, server_default="true"),
        sa.Column("notify_slack", sa.Boolean, server_default="false"),
        sa.Column("slack_webhook", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_alert_rules_ws_enabled", "alert_rules", ["workspace_id", "is_enabled"])

    # ── chat_sessions ──────────────────────────────────────────────
    op.create_table(
        "chat_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("last_active_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_index("idx_chat_sessions_ws_user", "chat_sessions", ["workspace_id", "user_id"])

    # ── chat_messages ──────────────────────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("sources_json", JSONB, nullable=True),
        sa.Column("confidence", sa.String(10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("idx_chat_msg_session", "chat_messages", ["session_id", "created_at"])

    # ── forecast_results ───────────────────────────────────────────
    op.create_table(
        "forecast_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scenario", sa.String(20), nullable=False),
        sa.Column("horizon_months", sa.SmallInteger, nullable=False),
        sa.Column("result_json", JSONB, nullable=False),
        sa.Column("model_version", sa.String(20), nullable=False, server_default="v1_linear"),
        sa.Column("data_hash", sa.String(64), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_forecast_ws_scenario", "forecast_results", ["workspace_id", "scenario"])

    # ── audit_logs ─────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("old_value", JSONB, nullable=True),
        sa.Column("new_value", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("idx_audit_ws_time", "audit_logs", ["workspace_id", "created_at"])
    op.create_index("idx_audit_entity", "audit_logs", ["entity_type", "entity_id"])

    # ── industry_benchmarks ────────────────────────────────────────
    op.create_table(
        "industry_benchmarks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("industry", sa.String(50), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("metric_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False, server_default="percentage"),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("year", sa.SmallInteger, nullable=False, server_default="2025"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_benchmark_unique", "industry_benchmarks", ["industry", "metric_name", "year"], unique=True)

    # ── plaid_items ────────────────────────────────────────────────
    op.create_table(
        "plaid_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("item_id", sa.String(255), nullable=False),
        sa.Column("access_token_encrypted", sa.Text, nullable=False),
        sa.Column("institution_id", sa.String(50), nullable=True),
        sa.Column("institution_name", sa.String(255), nullable=True),
        sa.Column("sync_cursor", sa.Text, nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_plaid_items_user_id", "plaid_items", ["user_id"])
    op.create_index("idx_plaid_ws_item", "plaid_items", ["workspace_id", "item_id"], unique=True)


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    tables = [
        "plaid_items", "industry_benchmarks", "audit_logs",
        "forecast_results", "chat_messages", "chat_sessions",
        "alert_rules", "alerts", "goals", "budgets",
        "transactions", "users", "workspaces",
    ]
    for table in tables:
        op.drop_table(table)

    # Drop custom enum types
    for enum_name in ["userrole", "transactiontype", "alertseverity", "goalstatus"]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name};")
