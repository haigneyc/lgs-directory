"""add store slug column for human-readable URLs

Revision ID: c5e1a9f4b2d8
Revises: b4f2e9a1c3d5
Create Date: 2026-04-06 00:00:00.000000

Adds a ``slug`` column to ``stores`` to back human-readable URLs of the
form ``/store/<store-name>-<city>-<state-abbr>`` (Vera Rec 3,
rollforstore-seo-analysis-2026-04-06.md). UUID URLs carry zero keyword
or CTR signal; slugs improve both.

Migration strategy (deploy in two passes):

1. This migration creates the column as ``NULLABLE`` plus a partial
   unique index that only covers populated rows. That makes the
   migration safe to run against a populated ``stores`` table without
   needing to coordinate with the backfill step.
2. After applying this migration, run
   ``scripts/backfill_store_slugs.py`` to populate every existing row.
3. A follow-up migration (out of scope for this PR -- gated on backfill
   completion) will ``ALTER COLUMN slug SET NOT NULL`` and replace the
   partial index with a full unique index.

The partial unique index protects us from collisions during the rolling
backfill while still letting unfilled rows coexist.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c5e1a9f4b2d8"
down_revision: Union[str, Sequence[str], None] = "b4f2e9a1c3d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable slug column and partial unique index."""
    op.add_column(
        "stores",
        sa.Column("slug", sa.String(length=160), nullable=True),
    )
    # CONCURRENTLY so the index build does not block writes on the
    # populated stores table. Cannot run inside a transaction block.
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS
              ux_stores_slug
              ON stores (slug)
              WHERE slug IS NOT NULL
            """
        )


def downgrade() -> None:
    """Drop slug column and its unique index."""
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ux_stores_slug")
    op.drop_column("stores", "slug")
