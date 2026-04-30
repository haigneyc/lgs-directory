"""Store slug generation and public-indexability guardrails."""

from __future__ import annotations

import re
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from lgs_directory.models.enums import StoreStatus

MAX_STORE_SLUG_LENGTH = 160
SHORT_ID_LENGTH = 6
PUBLIC_STORE_STATUSES = frozenset({
    StoreStatus.ACTIVE,
    StoreStatus.VERIFIED,
    StoreStatus.CANDIDATE,
})

_NON_SLUG_CHARS = re.compile(r"[^a-z0-9 -]")
_WHITESPACE = re.compile(r"\s+")
_DASH_RUN = re.compile(r"-{2,}")
_LEADING_TRAILING_DASH = re.compile(r"^-+|-+$")
_QUOTE_CHARS = re.compile(r"['\u2018\u2019\u201B\u201C\u201D\u201F\"]")
_LEGAL_SUFFIX_REGEX = re.compile(
    r"[,\s]+(l\.?l\.?c\.?|inc\.?|incorporated|corp\.?|corporation|"
    r"ltd\.?|limited|co\.?|company)\s*$",
    re.IGNORECASE,
)

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


def normalize_state_slug_component(raw: str | None) -> str:
    """Return a lowercase state abbreviation or slug-safe state token."""
    assert raw is None or isinstance(raw, str), "state must be string or None"
    if raw is None:
        return ""
    state = raw.strip().lower()
    if len(state) == 2:
        return state
    return _STATE_NAME_TO_ABBR.get(state, state.replace(" ", "-"))


def _strip_legal_suffix(name: str) -> str:
    """Strip trailing legal-entity tokens from a store name."""
    assert isinstance(name, str), "name must be a string"
    cleaned = name
    for _ in range(4):
        next_value = _LEGAL_SUFFIX_REGEX.sub("", cleaned)
        if next_value == cleaned:
            break
        cleaned = next_value
    cleaned = cleaned.strip()
    return cleaned if len(cleaned) > 0 else name.strip()


def slug_part(value: str) -> str:
    """Convert a single string component into lowercase ASCII kebab-case."""
    assert isinstance(value, str), "value must be a string"
    lowered = value.lower()
    quoteless = _QUOTE_CHARS.sub("", lowered)
    ascii_safe = _NON_SLUG_CHARS.sub(" ", quoteless)
    dashed = _WHITESPACE.sub("-", ascii_safe.strip())
    collapsed = _DASH_RUN.sub("-", dashed)
    trimmed = _LEADING_TRAILING_DASH.sub("", collapsed)
    assert "--" not in trimmed, "slug part contains double dashes"
    return trimmed


def build_store_slug(name: str, city: str, state_abbr: str) -> str:
    """Build the canonical ``<name>-<city>-<state>`` store slug."""
    assert isinstance(name, str) and len(name) > 0, "name must be non-empty"
    assert isinstance(city, str), "city must be a string"
    assert isinstance(state_abbr, str), "state_abbr must be a string"

    cleaned_name = _strip_legal_suffix(name)
    assert len(cleaned_name) > 0, "cleaned name must be non-empty"

    name_slug = slug_part(cleaned_name)
    city_slug = slug_part(city)
    state_slug = slug_part(state_abbr)
    assert len(name_slug) > 0, f"empty name slug for name={name!r}"

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
        parts = [name_slug]
    elif not has_city or name_ends_with_city:
        parts = [name_slug, state_slug] if has_state else [name_slug]
    else:
        parts = [name_slug, city_slug, state_slug] if has_state else [name_slug, city_slug]

    combined = "-".join(part for part in parts if len(part) > 0)
    collapsed = _DASH_RUN.sub("-", combined)
    trimmed = _LEADING_TRAILING_DASH.sub("", collapsed)
    if len(trimmed) > MAX_STORE_SLUG_LENGTH:
        trimmed = _LEADING_TRAILING_DASH.sub("", trimmed[:MAX_STORE_SLUG_LENGTH])

    assert len(trimmed) > 0, f"empty slug for name={name!r}"
    assert len(trimmed) <= MAX_STORE_SLUG_LENGTH, "slug exceeds max length"
    assert "--" not in trimmed, "slug contains double dashes"
    return trimmed


def disambiguate_slug(base: str, store_uuid: str) -> str:
    """Append a short UUID prefix to break a slug collision."""
    assert isinstance(base, str) and len(base) > 0, "base must be non-empty"
    assert isinstance(store_uuid, str), "store_uuid must be a string"
    suffix = store_uuid.replace("-", "")[:SHORT_ID_LENGTH].lower()
    assert len(suffix) == SHORT_ID_LENGTH, "short id has unexpected length"
    candidate = f"{base}-{suffix}"
    if len(candidate) > MAX_STORE_SLUG_LENGTH:
        keep = MAX_STORE_SLUG_LENGTH - len(suffix) - 1
        candidate = f"{base[:keep].rstrip('-')}-{suffix}"
    assert "--" not in candidate, "disambiguated slug has double dashes"
    return candidate


def ensure_public_store_slug(store: object, session: Session) -> bool:
    """Assign a unique slug before a store becomes public/indexable."""
    from lgs_directory.models.store import Store

    assert isinstance(store, Store), "store must be a Store"
    assert isinstance(session, Session), "session must be a Session"

    status = StoreStatus(store.status)
    current_slug = store.slug.strip() if isinstance(store.slug, str) else ""
    if status not in PUBLIC_STORE_STATUSES or len(current_slug) > 0:
        return False

    if store.id is None:
        store.id = uuid4()
    assert store.id is not None, "store id must be populated before slug generation"
    assert isinstance(store.address, dict), "store address must be a dict"

    city = str(store.address.get("city") or "")
    state = normalize_state_slug_component(store.address.get("state"))
    base = build_store_slug(store.name, city, state)
    slug = base

    existing = session.execute(
        select(Store.id).where(Store.slug == slug).limit(1)
    ).scalar_one_or_none()
    if existing is not None and existing != store.id:
        slug = disambiguate_slug(base, str(store.id))

    store.slug = slug
    assert store.slug is not None and len(store.slug) > 0, "store slug must be populated"
    return True
