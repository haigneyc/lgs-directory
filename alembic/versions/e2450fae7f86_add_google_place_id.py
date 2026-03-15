"""add google_place_id

Revision ID: e2450fae7f86
Revises: 865ee3ccf432
Create Date: 2026-03-13 13:50:47.047864

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2450fae7f86'
down_revision: Union[str, Sequence[str], None] = '865ee3ccf432'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('stores', sa.Column('google_place_id', sa.String(length=100), nullable=True))
    op.create_index('ix_stores_google_place_id', 'stores', ['google_place_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_stores_google_place_id', table_name='stores')
    op.drop_column('stores', 'google_place_id')
