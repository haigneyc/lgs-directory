"""perf indexes: state expression, UPPER(state,city), partial latlng on active stores

Revision ID: b4f2e9a1c3d5
Revises: d7a3b1c9e4f2
Create Date: 2026-04-06 00:00:00.000000

Adds three performance indexes per Nox perf audit (rollforstore):

- REM-005 / QW-4: expression index on ``stores((address->>'state'))``
  to turn state-slug filtering from a seq scan into an index seek
  (PERF-010 in the audit).
- REM-007 / QW-4: compound expression index on
  ``(UPPER(address->>'state'), UPPER(address->>'city'))`` for the
  case-insensitive city lookups used by ``/stores/[state]/[city]`` and
  ``getOtherStoresInCity`` (PERF-010).
- REM-008 / QW-5: partial ``(latitude, longitude)`` index on active /
  verified / candidate stores with non-null coordinates to back the
  bounding-box pre-filter in ``getNearbyStores`` and the
  ``/api/stores/nearby`` route (PERF-009).

All three are created with ``CREATE INDEX CONCURRENTLY IF NOT EXISTS``
so they are safe and idempotent against production data. Because
``CONCURRENTLY`` cannot run inside a transaction block, this migration
disables Alembic's implicit transaction via
``with op.get_context().autocommit_block()``.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b4f2e9a1c3d5"
down_revision: Union[str, Sequence[str], None] = "d7a3b1c9e4f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create perf indexes concurrently and idempotently."""
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stores_state
              ON stores ((address->>'state'))
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stores_state_city_upper
              ON stores ((UPPER(address->>'state')), (UPPER(address->>'city')))
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stores_latlng_active
              ON stores (latitude, longitude)
              WHERE status IN ('active', 'verified', 'candidate')
                AND latitude IS NOT NULL
                AND longitude IS NOT NULL
            """
        )


def downgrade() -> None:
    """Drop perf indexes concurrently and idempotently."""
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_stores_latlng_active")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_stores_state_city_upper")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_stores_state")
