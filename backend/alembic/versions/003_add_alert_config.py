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
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'workspaces' AND column_name = 'alert_config'
            ) THEN
                ALTER TABLE workspaces ADD COLUMN alert_config JSONB;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE workspaces DROP COLUMN IF EXISTS alert_config;")
