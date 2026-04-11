"""Add premium store listings: columns on stores + store_claims + store_events tables

Revision ID: f1a2b3c4d5e6
Revises: e8a1b2c3d4f5
Create Date: 2026-04-11 00:00:00.000000

Adds support for the "Claim this store" / premium listing feature:

1. ``stores`` table gets five new nullable columns:
   - ``claimed_by_email`` (text) — set on claim approval
   - ``claimed_at`` (timestamptz) — when the claim was approved
   - ``premium_status`` (text) — null / 'claimed' / 'premium'
   - ``premium_until`` (timestamptz) — set by Stripe webhook
   - ``hero_image_url`` (text) — premium hero banner image

2. New ``store_claims`` table to hold ownership claim submissions.

3. New ``store_events`` table to hold premium store events.

All columns are nullable to make the migration additive and safe to
apply without downtime.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e8a1b2c3d4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add premium listing columns and tables."""
    # --- stores table: new columns ---
    op.add_column(
        "stores",
        sa.Column("claimed_by_email", sa.Text(), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "stores",
        sa.Column("premium_status", sa.Text(), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column(
            "premium_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "stores",
        sa.Column("hero_image_url", sa.Text(), nullable=True),
    )

    # --- store_claims table ---
    op.create_table(
        "store_claims",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "store_id",
            sa.Uuid(),
            sa.ForeignKey("stores.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("proof_text", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_store_claims_store_id",
        "store_claims",
        ["store_id"],
    )

    # --- store_events table ---
    op.create_table(
        "store_events",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "store_id",
            sa.Uuid(),
            sa.ForeignKey("stores.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_store_events_store_id",
        "store_events",
        ["store_id"],
    )


def downgrade() -> None:
    """Remove premium listing columns and tables."""
    op.drop_table("store_events")
    op.drop_table("store_claims")

    op.drop_column("stores", "hero_image_url")
    op.drop_column("stores", "premium_until")
    op.drop_column("stores", "premium_status")
    op.drop_column("stores", "claimed_at")
    op.drop_column("stores", "claimed_by_email")
