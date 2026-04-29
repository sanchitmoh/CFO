"""
003: Add alert_config JSONB column to workspaces table.
Stores workspace-level alert thresholds and notification preferences.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "003_add_alert_config"
down_revision = "e97b5b5924ab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("alert_config", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "alert_config")
