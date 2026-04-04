"""add store_categories junction table

Revision ID: f6281884d0c3
Revises: e2450fae7f86
Create Date: 2026-04-03 21:03:53.424990

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f6281884d0c3'
down_revision: Union[str, Sequence[str], None] = 'e2450fae7f86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('store_categories',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('store_id', sa.Uuid(), nullable=False),
    sa.Column('category', sa.String(length=30), nullable=False),
    sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('store_id', 'category')
    )
    op.create_index('ix_store_categories_category', 'store_categories', ['category'], unique=False)
    op.create_index('ix_store_categories_store_id', 'store_categories', ['store_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_store_categories_store_id', table_name='store_categories')
    op.drop_index('ix_store_categories_category', table_name='store_categories')
    op.drop_table('store_categories')
