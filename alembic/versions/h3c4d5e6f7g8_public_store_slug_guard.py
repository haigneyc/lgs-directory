"""add not-valid guard for public store slugs

Revision ID: h3c4d5e6f7g8
Revises: g2b3c4d5e6f7
Create Date: 2026-04-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "h3c4d5e6f7g8"
down_revision: Union[str, Sequence[str], None] = "g2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Require slugs for newly written public/indexable store rows."""
    op.execute(
        """
        ALTER TABLE stores
        ADD CONSTRAINT ck_stores_public_status_requires_slug
        CHECK (
          status NOT IN ('active', 'verified', 'candidate')
          OR (slug IS NOT NULL AND btrim(slug) <> '')
        )
        NOT VALID
        """
    )


def downgrade() -> None:
    """Remove the public slug guardrail."""
    op.execute(
        """
        ALTER TABLE stores
        DROP CONSTRAINT IF EXISTS ck_stores_public_status_requires_slug
        """
    )
