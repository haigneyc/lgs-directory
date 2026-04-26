"""OSM state discovery — defensive store_external_refs + pending_review status.

Revision ID: d8c4f1a9b3e7
Revises: f1a2b3c4d5e6
Create Date: 2026-04-25 21:05:00.000000

Adds infrastructure for the OSM-for-LGS state-by-state discovery pipeline
(see docs/exec-plans/active/research-pipeline-improvements.md and the
spec at Outbox/2026-04-25/soren-osm-lgs-spec.md):

1. Defensive ``CREATE TABLE IF NOT EXISTS`` for ``store_external_refs``.
   The model has existed in code since the LFS/multi-source merge but the
   table was created out-of-band on production without a tracked alembic
   migration (per the "MCP apply_migration bypasses alembic" Jarvis
   memory). This migration formalises the schema so a fresh checkout
   migrates cleanly.
2. ``pending_review`` is a new ``StoreStatus`` value used by the OSM
   pipeline to hide low-confidence rows from the public site until a
   content scrape promotes them. The ``stores.status`` column is
   ``VARCHAR(20)`` with no DB-side enum/check constraint, so accepting
   the new value is purely a Python-side concern; this migration adds
   no DDL for it but documents the value here for future readers.
3. ``DiscoverySource.OSM_OVERPASS`` is similarly a new Python enum value
   that fits inside the existing ``VARCHAR(30)`` widened by
   ``a1b2c3d4e5f6``. No DDL needed.

Phase 1 explicitly defers making ``stores.address`` nullable. OSM rows
without complete ``addr:*`` tags are dropped at the ingest layer
(see ``discovery/ingest_osm.py::_parse_osm_address``); the schema
invariant that every persisted store has a full address is preserved.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d8c4f1a9b3e7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create store_external_refs if it doesn't already exist on prod."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS store_external_refs (
            id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
            store_id     uuid        NOT NULL
                                     REFERENCES stores(id) ON DELETE CASCADE,
            provider     varchar(50) NOT NULL,
            external_id  varchar(255) NOT NULL,
            payload      jsonb,
            first_seen   timestamp   NOT NULL DEFAULT now(),
            last_seen    timestamp   NOT NULL DEFAULT now(),
            CONSTRAINT uq_store_external_refs_provider_external_id
                UNIQUE (provider, external_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_store_external_refs_store_id
            ON store_external_refs (store_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_store_external_refs_provider
            ON store_external_refs (provider)
        """
    )


def downgrade() -> None:
    """Defensive downgrade — leaves the table in place if other code depends on it.

    Dropping ``store_external_refs`` would cascade-break every existing
    cross-source dedup path (WPN, Games Workshop, comics, retro games,
    OSM). Downgrade is a no-op so that re-applying the migration after a
    rollback does not lose production data.
    """
    pass
