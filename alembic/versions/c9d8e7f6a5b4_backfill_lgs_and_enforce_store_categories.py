"""backfill lgs category and enforce valid store_categories values

Revision ID: c9d8e7f6a5b4
Revises: a1b2c3d4e5f6
Create Date: 2026-04-04 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a category validity check and seed lgs for legacy store rows."""
    op.create_check_constraint(
        "ck_store_categories_valid_category",
        "store_categories",
        "category IN ('lgs', 'comic_shop', 'retro_games', 'hobby_miniatures')",
    )
    op.execute(
        """
        INSERT INTO store_categories (store_id, category)
        SELECT s.id, 'lgs'
        FROM stores s
        WHERE s.discovery_source IN ('wpn', 'google_places', 'manual', 'tcgplayer')
          AND NOT EXISTS (
              SELECT 1
              FROM store_categories sc
              WHERE sc.store_id = s.id
                AND sc.category = 'lgs'
          )
        """
    )


def downgrade() -> None:
    """Drop the category validity check."""
    op.drop_constraint(
        "ck_store_categories_valid_category",
        "store_categories",
        type_="check",
    )
