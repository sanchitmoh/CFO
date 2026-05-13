"""merge_phase2_migrations

Revision ID: caecac09d29a
Revises: 14d3d382c16c, b8f3a2d1e9c4
Create Date: 2026-05-14 01:04:01.651300

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'caecac09d29a'
down_revision: Union[str, None] = ('14d3d382c16c', 'b8f3a2d1e9c4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
