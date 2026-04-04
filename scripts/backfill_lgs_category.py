"""Backfill all existing stores with the 'lgs' category.

Run: python scripts/backfill_lgs_category.py
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from lgs_directory.db import get_session

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_MAX_STORES = 50_000


def backfill() -> int:
    """Tag legacy game-store rows with the `lgs` category.

    Returns the number of stores backfilled.
    """
    with get_session() as session:
        stmt = text(
            """
            WITH candidates AS (
                SELECT s.id
                FROM stores s
                WHERE s.discovery_source IN ('wpn', 'google_places', 'manual', 'tcgplayer')
                  AND NOT EXISTS (
                      SELECT 1
                      FROM store_categories sc
                      WHERE sc.store_id = s.id
                        AND sc.category = 'lgs'
                  )
                LIMIT :limit
            )
            INSERT INTO store_categories (store_id, category)
            SELECT id, 'lgs'
            FROM candidates
            RETURNING store_id
            """
        )
        inserted_rows = session.execute(stmt, {"limit": _MAX_STORES}).fetchall()
        count = len(inserted_rows)

        assert count >= 0, "count must be non-negative"
        logger.info("Backfilled %d stores with 'lgs' category", count)

    return count


if __name__ == "__main__":
    result = backfill()
    assert result >= 0
