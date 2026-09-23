"""ADVANCE-005: Add pgvector extension and embedding column to transactions.

Creates the vector extension, adds a 384-dim embedding column to transactions,
and creates an IVFFlat index for fast cosine similarity search.

Uses 384 dimensions for the free all-MiniLM-L6-v2 model.

Revision ID: 002_add_pgvector
Revises: 001_enable_rls
Create Date: 2026-04-19
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "002_add_pgvector"
down_revision = "001_enable_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Enable pgvector and add embedding column to transactions."""
    # Enable the vector extension (Neon supports this natively)
    op.execute("""
        DO $$ BEGIN
            CREATE EXTENSION IF NOT EXISTS vector;
            ALTER TABLE transactions ADD COLUMN IF NOT EXISTS description_vec vector(384);
            CREATE INDEX IF NOT EXISTS idx_txn_description_vec
            ON transactions USING ivfflat (description_vec vector_cosine_ops)
            WITH (lists = 50);
        EXCEPTION WHEN undefined_file OR feature_not_supported THEN
            RAISE NOTICE 'pgvector extension not installed on this PostgreSQL instance, skipping';
        END $$;
    """)


def downgrade() -> None:
    """Remove embedding column and extension."""
    op.execute("""
        DO $$ BEGIN
            DROP INDEX IF EXISTS idx_txn_description_vec;
            ALTER TABLE transactions DROP COLUMN IF EXISTS description_vec;
        EXCEPTION WHEN undefined_column OR undefined_table OR feature_not_supported THEN
            NULL;
        END $$;
    """)
