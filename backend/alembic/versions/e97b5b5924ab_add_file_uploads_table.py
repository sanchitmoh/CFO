"""add_file_uploads_table

Revision ID: e97b5b5924ab
Revises: 002_add_pgvector
Create Date: 2026-04-23 12:43:39.711574

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e97b5b5924ab'
down_revision: Union[str, None] = '002_add_pgvector'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # FILE-001: file_uploads table for CSV upload audit trail
    # Pure SQL to avoid SQLAlchemy Enum auto-creation issues
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE fileuploadstatus AS ENUM ('pending', 'processed', 'failed', 'duplicate');
        EXCEPTION WHEN duplicate_object THEN
            NULL;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS file_uploads (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            user_id         UUID NOT NULL REFERENCES users(id),
            filename        VARCHAR(255) NOT NULL,
            file_size       INTEGER NOT NULL,
            content_hash    VARCHAR(64) NOT NULL,
            storage_path    VARCHAR(500) NOT NULL,
            row_count       INTEGER NOT NULL DEFAULT 0,
            error_count     INTEGER NOT NULL DEFAULT 0,
            status          fileuploadstatus DEFAULT 'pending',
            error_details   JSONB,
            created_at      TIMESTAMPTZ DEFAULT now()
        );
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_file_uploads_user_id ON file_uploads (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_file_upload_ws_hash ON file_uploads (workspace_id, content_hash);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_file_upload_ws_created ON file_uploads (workspace_id, created_at);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS file_uploads;")
    op.execute("DROP TYPE IF EXISTS fileuploadstatus;")
