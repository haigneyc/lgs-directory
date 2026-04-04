"""widen discovery_source column to String(30)

Revision ID: a1b2c3d4e5f6
Revises: f6281884d0c3
Create Date: 2026-04-03 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f6281884d0c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Widen discovery_source from VARCHAR(20) to VARCHAR(30)."""
    op.alter_column(
        'stores',
        'discovery_source',
        type_=sa.String(length=30),
        existing_type=sa.String(length=20),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Revert discovery_source back to VARCHAR(20)."""
    op.alter_column(
        'stores',
        'discovery_source',
        type_=sa.String(length=20),
        existing_type=sa.String(length=30),
        existing_nullable=False,
    )
