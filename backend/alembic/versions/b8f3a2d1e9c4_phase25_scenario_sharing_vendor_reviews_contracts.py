"""Phase 2.5: Add scenario sharing, vendor reviews, and vendor contracts tables.

Revision ID: b8f3a2d1e9c4
Revises: a407d9456dbd
Create Date: 2026-05-09 17:00:00.000000+05:30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b8f3a2d1e9c4"
down_revision = "a407d9456dbd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Scenario Shares ───────────────────────────────────────────
    op.create_table(
        "scenario_shares",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shared_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shared_with_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission", sa.String(20), server_default="viewer", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_scenario_shares_workspace", "scenario_shares", ["workspace_id"])
    op.create_index("ix_scenario_shares_scenario", "scenario_shares", ["scenario_id"])
    op.create_index("ix_scenario_shares_shared_with", "scenario_shares", ["shared_with_user_id"])

    # ── Vendor Reviews ────────────────────────────────────────────
    op.create_table(
        "vendor_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("delivery_rating", sa.Integer, nullable=False),
        sa.Column("quality_rating", sa.Integer, nullable=False),
        sa.Column("responsiveness_rating", sa.Integer, nullable=False),
        sa.Column("cost_rating", sa.Integer, nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("review_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_vendor_reviews_workspace", "vendor_reviews", ["workspace_id"])
    op.create_index("ix_vendor_reviews_vendor", "vendor_reviews", ["vendor_id"])

    # ── Vendor Contracts ──────────────────────────────────────────
    op.create_table(
        "vendor_contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("contract_type", sa.String(50), server_default="service", nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Numeric(15, 2), nullable=True),
        sa.Column("auto_renew", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("renewal_notice_days", sa.Integer, server_default=sa.text("30"), nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_vendor_contracts_workspace", "vendor_contracts", ["workspace_id"])
    op.create_index("ix_vendor_contracts_vendor", "vendor_contracts", ["vendor_id"])
    op.create_index("ix_vendor_contracts_status", "vendor_contracts", ["status"])
    op.create_index("ix_vendor_contracts_end_date", "vendor_contracts", ["end_date"])

    # ── RLS Policies ──────────────────────────────────────────────
    for table in ["scenario_shares", "vendor_reviews", "vendor_contracts"]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY workspace_isolation ON {table}
            USING (workspace_id = current_setting('app.workspace_id')::uuid)
        """)


def downgrade() -> None:
    for table in ["vendor_contracts", "vendor_reviews", "scenario_shares"]:
        op.execute(f"DROP POLICY IF EXISTS workspace_isolation ON {table}")
        op.drop_table(table)
