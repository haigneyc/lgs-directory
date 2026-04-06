"""add riftbound to category check constraint

Revision ID: d7a3b1c9e4f2
Revises: c9d8e7f6a5b4
Create Date: 2026-04-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d7a3b1c9e4f2"
down_revision: Union[str, Sequence[str], None] = "c9d8e7f6a5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace the category CHECK constraint to include 'riftbound'."""
    op.drop_constraint(
        "ck_store_categories_valid_category",
        "store_categories",
        type_="check",
    )
    op.create_check_constraint(
        "ck_store_categories_valid_category",
        "store_categories",
        "category IN ('lgs', 'comic_shop', 'retro_games', 'hobby_miniatures', 'riftbound')",
    )


def downgrade() -> None:
    """Revert to the original CHECK constraint without 'riftbound'."""
    op.drop_constraint(
        "ck_store_categories_valid_category",
        "store_categories",
        type_="check",
    )
    op.create_check_constraint(
        "ck_store_categories_valid_category",
        "store_categories",
        "category IN ('lgs', 'comic_shop', 'retro_games', 'hobby_miniatures')",
    )
