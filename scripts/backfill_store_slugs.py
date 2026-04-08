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
# Quote characters (straight + curly) stripped ENTIRELY before
# slugification, so "Jan's" becomes "jans" rather than "jan-s". Must
# stay in sync with QUOTE_CHARS_REGEX in web/lib/slugs.ts.
_QUOTE_CHARS = re.compile(r"['\u2018\u2019\u201B\u201C\u201D\u201F\"]")
# Trailing legal-entity tokens stripped from the store name before
# slugification. Case-insensitive, only at the end of the string,
# optionally preceded by a comma and whitespace. Must stay in sync with
# LEGAL_SUFFIX_REGEX in web/lib/slugs.ts.
#
# Worked examples (mirrors web/lib/slugs.ts):
#   "Jan's Tropical Fish"   -> "jans-tropical-fish"
#   "Bob's Tropical Fish"   -> "bobs-tropical-fish"
#   "Starjumpers Tank LLC"  -> "starjumpers-tank"
#   "Pam's Pets & Fish"     -> "pams-pets-fish"
#   "Aqua Cave Inc."        -> "aqua-cave"
#   "Fish R Us, Co."        -> "fish-r-us"
#   "A-Z Aquatic LLC"       -> "a-z-aquatic"
#   "The Fish People"       -> "the-fish-people"
#   "Co Company Stores"     -> "co-company-stores" (mid-name, not stripped)
_LEGAL_SUFFIX_REGEX = re.compile(
    r"[,\s]+(l\.?l\.?c\.?|inc\.?|incorporated|corp\.?|corporation|"
    r"ltd\.?|limited|co\.?|company)\s*$",
    re.IGNORECASE,
)


def _strip_legal_suffix(name: str) -> str:
    """Strip trailing legal-entity tokens from a store name.

    Applied repeatedly so "Foo Inc, LLC" loses both tokens. Falls back
    to the original name if stripping would leave an empty string.
    """
    assert isinstance(name, str), "name must be a string"
    cleaned = name
    for _ in range(4):
        nxt = _LEGAL_SUFFIX_REGEX.sub("", cleaned)
        if nxt == cleaned:
            break
        cleaned = nxt
    cleaned = cleaned.strip()
    if len(cleaned) == 0:
        return name.strip()
    return cleaned

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


def _slug_part(value: str) -> str:
    """Run the standard slugify pipeline on a single string component.

    Lowercases, strips quotes entirely, then maps anything outside
    ``[a-z0-9 -]`` to a space, collapses whitespace and dash runs, and
    trims leading/trailing dashes. Returns an empty string if the input
    has no slug-safe characters.
    """
    assert isinstance(value, str), "value must be a string"
    lowered = value.lower()
    quoteless = _QUOTE_CHARS.sub("", lowered)
    ascii_safe = _NON_SLUG_CHARS.sub(" ", quoteless)
    dashed = _WHITESPACE.sub("-", ascii_safe.strip())
    collapsed = _DASH_RUN.sub("-", dashed)
    trimmed = _LEADING_TRAILING_DASH.sub("", collapsed)
    assert "--" not in trimmed, "slug part contains double dashes"
    return trimmed


def _slugify(name: str, city: str, state_abbr: str) -> str:
    """Build the canonical slug for a store row.

    Mirrors ``buildStoreSlug`` in ``web/lib/slugs.ts``. Slugifies the
    name and city independently so we can detect when the store name
    already ends with the city (e.g. "HobbyTown Sioux Falls" in Sioux
    Falls, SD) and skip the redundant city append. Asserts on every
    branch so a regression in either side is caught immediately.
    """
    assert isinstance(name, str) and len(name) > 0, "name must be non-empty"
    assert isinstance(city, str), "city must be a string"
    assert isinstance(state_abbr, str), "state_abbr must be a string"

    cleaned_name = _strip_legal_suffix(name)
    assert len(cleaned_name) > 0, "cleaned name must be non-empty"

    name_slug = _slug_part(cleaned_name)
    city_slug = _slug_part(city)
    state_slug = _slug_part(state_abbr)
    assert len(name_slug) > 0, f"empty name slug for name={name!r}"

    # De-duplicate city when the store name already ends with it (full
    # suffix match on the SLUG forms only -- avoids partial-word false
    # positives like "Game Stop" / "Gamestown"). Check the longer
    # ``-city-state`` suffix BEFORE the shorter ``-city`` suffix, so
    # names like "Game X Change Gainesville TX" in Gainesville, TX emit
    # as-is rather than appending "-tx" twice.
    has_city = len(city_slug) > 0
    has_state = len(state_slug) > 0
    city_state_suffix = f"-{city_slug}-{state_slug}"
    city_state_whole = f"{city_slug}-{state_slug}"
    city_suffix = f"-{city_slug}"
    name_ends_with_city_state = (
        has_city
        and has_state
        and (name_slug == city_state_whole or name_slug.endswith(city_state_suffix))
    )
    name_ends_with_city = has_city and (
        name_slug == city_slug or name_slug.endswith(city_suffix)
    )
    if name_ends_with_city_state:
        # Name already contains "-city-state"; emit the name as-is.
        parts = [name_slug]
    elif not has_city or name_ends_with_city:
        parts = [name_slug, state_slug] if has_state else [name_slug]
    else:
        parts = [name_slug, city_slug, state_slug] if has_state else [name_slug, city_slug]

    combined = "-".join(p for p in parts if len(p) > 0)
    collapsed = _DASH_RUN.sub("-", combined)
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
