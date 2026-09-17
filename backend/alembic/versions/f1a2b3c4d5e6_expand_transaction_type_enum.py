"""expand_transaction_type_enum

Revision ID: f1a2b3c4d5e6
Revises: caecac09d29a
Create Date: 2026-09-17 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'caecac09d29a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'credit'")
        op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'debit'")
        op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'transfer'")
        op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'refund'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum type directly
    pass
