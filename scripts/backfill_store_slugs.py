"""Backfill ``stores.slug`` with human-readable URL slugs.

Implements Vera Rec 3 (rollforstore-seo-analysis-2026-04-06.md): replace
the UUID-based ``/store/<uuid>`` URL with
``/store/<store-name>-<city>-<state-abbr>``. The slug column is added by
alembic ``c5e1a9f4b2d8_add_store_slug.py``; this script must run AFTER
that migration and BEFORE any follow-up migration that promotes the
column to ``NOT NULL``.

Slug shape mirrors ``buildStoreSlug`` in ``web/lib/slugs.ts``: lowercase
ASCII, kebab-case, double-dashes collapsed, leading/trailing hyphens
trimmed, hard-capped at 160 characters.

Collision handling: if two stores share the same name+city+state
(e.g. a chain), the second store appends ``-<short-id>`` where
``<short-id>`` is the first 6 characters of the row's UUID. The first 6
hex chars of a v4 UUID give 16^6 = 16M values, which is more than
sufficient to disambiguate the long tail.

Idempotent: running the script twice is a no-op for rows that already
have a populated slug.

Run: ``python scripts/backfill_store_slugs.py [--dry-run]``
"""

from __future__ import annotations

import argparse
import logging

from sqlalchemy import text

from lgs_directory.db import get_session
from lgs_directory.slug import (
    build_store_slug,
    disambiguate_slug,
    normalize_state_slug_component,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_MAX_STORES = 50_000
def backfill(dry_run: bool) -> int:
    """Populate ``stores.slug`` for every row that does not yet have one.

    Returns the number of rows updated.
    """
    assert isinstance(dry_run, bool), "dry_run must be a bool"

    updated = 0
    used: set[str] = set()

    with get_session() as session:
        rows = session.execute(
            text(
                """
                SELECT id::text AS id, name, address, slug
                FROM stores
                ORDER BY first_seen ASC
                LIMIT :limit
                """
            ),
            {"limit": _MAX_STORES},
        ).mappings().all()

        # Seed the in-memory uniqueness set with already-populated slugs
        # so reruns don't collide with themselves.
        for row in rows:
            existing = row["slug"]
            if existing:
                used.add(existing)

        for row in rows:
            if row["slug"]:
                continue
            address = row["address"] or {}
            assert isinstance(address, dict), "address must decode to a dict"
            city = address.get("city") or ""
            state_abbr = normalize_state_slug_component(address.get("state"))
            base = build_store_slug(row["name"], city, state_abbr)

            slug = base
            if slug in used:
                slug = disambiguate_slug(base, row["id"])
                assert slug not in used, "disambiguated slug still collides"
            used.add(slug)

            if dry_run:
                logger.info("would set slug %s -> %s", row["id"], slug)
            else:
                session.execute(
                    text("UPDATE stores SET slug = :slug WHERE id = :id"),
                    {"slug": slug, "id": row["id"]},
                )
            updated += 1

        if dry_run:
            session.rollback()
        else:
            session.commit()

    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute slugs and log them without writing to the database.",
    )
    args = parser.parse_args()
    count = backfill(dry_run=args.dry_run)
    logger.info("backfilled %d store slugs (dry_run=%s)", count, args.dry_run)


if __name__ == "__main__":
    main()
