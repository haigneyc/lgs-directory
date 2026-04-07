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
import re
from typing import Optional

from sqlalchemy import text

from lgs_directory.db import get_session

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_MAX_STORES = 50_000
_MAX_SLUG_LENGTH = 160
_SHORT_ID_LENGTH = 6
_NON_SLUG_CHARS = re.compile(r"[^a-z0-9 -]")
_WHITESPACE = re.compile(r"\s+")
_DASH_RUN = re.compile(r"-{2,}")
_LEADING_TRAILING_DASH = re.compile(r"^-+|-+$")

_STATE_NAME_TO_ABBR = {
    "alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar",
    "california": "ca", "colorado": "co", "connecticut": "ct",
    "delaware": "de", "district of columbia": "dc", "florida": "fl",
    "georgia": "ga", "hawaii": "hi", "idaho": "id", "illinois": "il",
    "indiana": "in", "iowa": "ia", "kansas": "ks", "kentucky": "ky",
    "louisiana": "la", "maine": "me", "maryland": "md",
    "massachusetts": "ma", "michigan": "mi", "minnesota": "mn",
    "mississippi": "ms", "missouri": "mo", "montana": "mt",
    "nebraska": "ne", "nevada": "nv", "new hampshire": "nh",
    "new jersey": "nj", "new mexico": "nm", "new york": "ny",
    "north carolina": "nc", "north dakota": "nd", "ohio": "oh",
    "oklahoma": "ok", "oregon": "or", "pennsylvania": "pa",
    "rhode island": "ri", "south carolina": "sc", "south dakota": "sd",
    "tennessee": "tn", "texas": "tx", "utah": "ut", "vermont": "vt",
    "virginia": "va", "washington": "wa", "west virginia": "wv",
    "wisconsin": "wi", "wyoming": "wy",
}


def _normalize_state(raw: Optional[str]) -> str:
    """Return a 2-letter lowercase state abbreviation, or empty string."""
    assert raw is None or isinstance(raw, str), "state must be string or None"
    if raw is None:
        return ""
    s = raw.strip().lower()
    if len(s) == 2:
        return s
    return _STATE_NAME_TO_ABBR.get(s, s.replace(" ", "-"))


def _slugify(name: str, city: str, state_abbr: str) -> str:
    """Build the canonical slug for a store row.

    Mirrors ``buildStoreSlug`` in ``web/lib/slugs.ts``. Asserts on every
    branch so a regression in either side is caught immediately.
    """
    assert isinstance(name, str) and len(name) > 0, "name must be non-empty"
    assert isinstance(city, str), "city must be a string"
    assert isinstance(state_abbr, str), "state_abbr must be a string"

    joined = f"{name} {city} {state_abbr}".lower()
    ascii_safe = _NON_SLUG_CHARS.sub(" ", joined)
    dashed = _WHITESPACE.sub("-", ascii_safe)
    collapsed = _DASH_RUN.sub("-", dashed)
    trimmed = _LEADING_TRAILING_DASH.sub("", collapsed)
    if len(trimmed) > _MAX_SLUG_LENGTH:
        trimmed = trimmed[:_MAX_SLUG_LENGTH]
        trimmed = _LEADING_TRAILING_DASH.sub("", trimmed)

    assert len(trimmed) > 0, f"empty slug for name={name!r}"
    assert len(trimmed) <= _MAX_SLUG_LENGTH, "slug exceeds max length"
    assert "--" not in trimmed, "slug contains double dashes"
    return trimmed


def _disambiguate(base: str, store_uuid: str) -> str:
    """Append a short UUID prefix to break a slug collision."""
    assert isinstance(base, str) and len(base) > 0, "base must be non-empty"
    assert isinstance(store_uuid, str), "store_uuid must be a string"
    suffix = store_uuid.replace("-", "")[:_SHORT_ID_LENGTH].lower()
    assert len(suffix) == _SHORT_ID_LENGTH, "short id has unexpected length"
    candidate = f"{base}-{suffix}"
    if len(candidate) > _MAX_SLUG_LENGTH:
        # Trim the base, not the disambiguator -- the disambiguator is
        # the only thing that guarantees uniqueness.
        keep = _MAX_SLUG_LENGTH - len(suffix) - 1
        candidate = f"{base[:keep].rstrip('-')}-{suffix}"
    assert "--" not in candidate, "disambiguated slug has double dashes"
    return candidate


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
            state_abbr = _normalize_state(address.get("state"))
            base = _slugify(row["name"], city, state_abbr)

            slug = base
            if slug in used:
                slug = _disambiguate(base, row["id"])
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
