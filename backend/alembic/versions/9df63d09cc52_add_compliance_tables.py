"""add_compliance_tables

Revision ID: 9df63d09cc52
Revises: 003_add_alert_config
Create Date: 2026-04-28 20:00:58.913400

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9df63d09cc52'
down_revision: Union[str, None] = '003_add_alert_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # COMPLIANCE-004: GDPR/CCPA compliance tables
    
    # Create enums for compliance tables
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE consentstatus AS ENUM ('granted', 'withdrawn', 'pending');
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE dataexportstatus AS ENUM ('requested', 'processing', 'completed', 'failed', 'expired');
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE datadeletionstatus AS ENUM ('requested', 'scheduled', 'in_progress', 'completed', 'failed', 'cancelled');
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """)
    
    # User consent tracking table
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_consents (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id        UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            consent_type        VARCHAR(50) NOT NULL,
            status              consentstatus NOT NULL,
            granted_at          TIMESTAMPTZ,
            withdrawn_at        TIMESTAMPTZ,
            ip_address_hash     VARCHAR(64),
            user_agent_hash     VARCHAR(64),
            withdrawal_reason   TEXT,
            created_at          TIMESTAMPTZ DEFAULT now(),
            updated_at          TIMESTAMPTZ DEFAULT now()
        );
    """)
    
    # Data export requests table
    op.execute("""
        CREATE TABLE IF NOT EXISTS data_exports (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id        UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status              dataexportstatus NOT NULL,
            format              VARCHAR(10) NOT NULL DEFAULT 'json',
            file_path           TEXT,
            file_size_bytes     INTEGER,
            include_metadata    BOOLEAN DEFAULT true,
            error_message       TEXT,
            expires_at          TIMESTAMPTZ NOT NULL,
            created_at          TIMESTAMPTZ DEFAULT now(),
            completed_at        TIMESTAMPTZ
        );
    """)
    
    # Data deletion requests table
    op.execute("""
        CREATE TABLE IF NOT EXISTS data_deletions (
            id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id            UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status                  datadeletionstatus NOT NULL,
            reason                  TEXT,
            confirmation_token      VARCHAR(255),
            scheduled_at            TIMESTAMPTZ NOT NULL,
            grace_period_ends_at    TIMESTAMPTZ,
            executed_at             TIMESTAMPTZ,
            error_message           TEXT,
            deleted_records_count   INTEGER,
            created_at              TIMESTAMPTZ DEFAULT now()
        );
    """)
    
    # Retention policies table
    op.execute("""
        CREATE TABLE IF NOT EXISTS retention_policies (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id        UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            entity_type         VARCHAR(50) NOT NULL,
            retention_days      INTEGER NOT NULL,
            is_enabled          BOOLEAN DEFAULT true,
            last_cleanup_at     TIMESTAMPTZ,
            next_cleanup_at     TIMESTAMPTZ,
            cleanup_count       INTEGER DEFAULT 0,
            created_at          TIMESTAMPTZ DEFAULT now(),
            updated_at          TIMESTAMPTZ DEFAULT now()
        );
    """)
    
    # Create indexes for compliance tables
    op.execute("CREATE INDEX IF NOT EXISTS idx_consent_user_type ON user_consents (user_id, consent_type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_consent_ws_status ON user_consents (workspace_id, status);")
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_export_user_status ON data_exports (user_id, status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_export_ws_created ON data_exports (workspace_id, created_at);")
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_deletion_user_status ON data_deletions (user_id, status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_deletion_scheduled ON data_deletions (scheduled_at);")
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_retention_ws_entity ON retention_policies (workspace_id, entity_type);")
    
    # Create unique constraint for retention policies
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_retention_ws_entity_unique ON retention_policies (workspace_id, entity_type);")


def downgrade() -> None:
    # Drop tables in reverse order
    op.execute("DROP TABLE IF EXISTS retention_policies;")
    op.execute("DROP TABLE IF EXISTS data_deletions;")
    op.execute("DROP TABLE IF EXISTS data_exports;")
    op.execute("DROP TABLE IF EXISTS user_consents;")
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS datadeletionstatus;")
    op.execute("DROP TYPE IF EXISTS dataexportstatus;")
    op.execute("DROP TYPE IF EXISTS consentstatus;")
