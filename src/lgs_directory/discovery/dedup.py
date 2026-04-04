"""Deduplication pipeline — matches candidate stores against existing records."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from thefuzz import fuzz  # type: ignore[import-untyped]

from lgs_directory.discovery.normalize import normalize_address, normalize_name
from lgs_directory.models.store import Store
from lgs_directory.models.store_external_ref import StoreExternalRef


class MatchTier(IntEnum):
    """Dedup match tiers, ordered by confidence (lower = more confident)."""

    WPN_ID = 1
    NAME_ZIP = 2
    ADDRESS = 3
    FUZZY = 4


# Thresholds
_FUZZY_NAME_THRESHOLD = 85  # fuzz.ratio score
_PROXIMITY_MILES = 0.5
_EARTH_RADIUS_MILES = 3958.8


@dataclass(frozen=True)
class DeduplicationResult:
    """Result of a deduplication check against existing stores."""

    matched_store: Store | None
    match_tier: MatchTier | None
    confidence: float  # 0.0 - 1.0
    needs_review: bool  # True for low-confidence fuzzy matches

    @property
    def is_match(self) -> bool:
        """Whether a match was found."""
        return self.matched_store is not None


def _haversine_miles(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculate distance in miles between two lat/lng points."""
    assert -90 <= lat1 <= 90 and -90 <= lat2 <= 90
    assert -180 <= lon1 <= 180 and -180 <= lon2 <= 180

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = _EARTH_RADIUS_MILES * c
    assert distance >= 0
    return distance


def _normalize_existing_store(store: Store) -> dict[str, str]:
    """Extract and normalize address from an existing Store record."""
    assert store.address is not None, "Store must have an address"
    addr = store.address
    return normalize_address(
        street=addr.get("street", ""),
        city=addr.get("city", ""),
        state=addr.get("state", ""),
        zip_code=addr.get("zip_code", ""),
    )


def find_duplicate(
    candidate_name: str,
    candidate_address: dict[str, str],
    candidate_wpn_id: str | None,
    candidate_lat: float | None,
    candidate_lng: float | None,
    existing_stores: list[Store],
    candidate_google_place_id: str | None = None,
) -> DeduplicationResult:
    """Check if a candidate store is a duplicate of any existing store.

    Matching tiers (checked in order):
      0.5. Exact match on google_place_id (if both have one)
      1. Exact match on wpn_id (if both have one)
      2. Exact match on normalized_name + zip_code
      3. Exact match on normalized street + city + state
      4. Fuzzy name match (>85%) AND geographic proximity (<0.5 miles)

    Returns DeduplicationResult with match info or no-match.
    """
    assert isinstance(candidate_name, str) and len(candidate_name) > 0
    assert isinstance(candidate_address, dict)
    assert isinstance(existing_stores, list)

    norm_name = normalize_name(candidate_name)
    norm_addr = candidate_address  # Already normalized by caller

    # Tier 0.5: Exact Google Place ID match
    if candidate_google_place_id:
        for store in existing_stores:
            if store.google_place_id and store.google_place_id == candidate_google_place_id:
                return DeduplicationResult(
                    matched_store=store,
                    match_tier=MatchTier.WPN_ID,  # Same confidence tier
                    confidence=1.0,
                    needs_review=False,
                )

    # Tier 1: Exact WPN ID match
    if candidate_wpn_id:
        for store in existing_stores:
            if store.wpn_id and store.wpn_id == candidate_wpn_id:
                return DeduplicationResult(
                    matched_store=store,
                    match_tier=MatchTier.WPN_ID,
                    confidence=1.0,
                    needs_review=False,
                )

    # Tier 2: Normalized name + ZIP
    for store in existing_stores:
        existing_norm_name = normalize_name(store.name)
        existing_norm_addr = _normalize_existing_store(store)

        if (
            norm_name == existing_norm_name
            and norm_addr.get("zip_code") == existing_norm_addr.get("zip_code")
        ):
            return DeduplicationResult(
                matched_store=store,
                match_tier=MatchTier.NAME_ZIP,
                confidence=0.95,
                needs_review=False,
            )

    # Tier 3: Normalized street + city + state
    for store in existing_stores:
        existing_norm_addr = _normalize_existing_store(store)

        if (
            norm_addr.get("street") == existing_norm_addr.get("street")
            and norm_addr.get("city") == existing_norm_addr.get("city")
            and norm_addr.get("state") == existing_norm_addr.get("state")
            and norm_addr.get("street")  # Don't match on empty streets
        ):
            return DeduplicationResult(
                matched_store=store,
                match_tier=MatchTier.ADDRESS,
                confidence=0.90,
                needs_review=False,
            )

    # Tier 4: Fuzzy name + geographic proximity
    for store in existing_stores:
        existing_norm_name = normalize_name(store.name)
        score = fuzz.ratio(norm_name, existing_norm_name)

        if score >= _FUZZY_NAME_THRESHOLD:
            # Check geographic proximity
            close_enough = False

            if (
                candidate_lat is not None
                and candidate_lng is not None
                and store.latitude is not None
                and store.longitude is not None
            ):
                dist = _haversine_miles(
                    candidate_lat, candidate_lng,
                    store.latitude, store.longitude,
                )
                close_enough = dist <= _PROXIMITY_MILES
            else:
                # Fall back to same ZIP code
                existing_norm_addr = _normalize_existing_store(store)
                close_enough = (
                    norm_addr.get("zip_code") == existing_norm_addr.get("zip_code")
                )

            if close_enough:
                confidence = score / 100.0
                return DeduplicationResult(
                    matched_store=store,
                    match_tier=MatchTier.FUZZY,
                    confidence=confidence,
                    needs_review=confidence < 0.92,
                )

    # No match found
    return DeduplicationResult(
        matched_store=None,
        match_tier=None,
        confidence=0.0,
        needs_review=False,
    )


def find_by_external_ref(
    provider: str,
    external_id: str,
    session: Session,
) -> Store | None:
    """Fast exact-match lookup via the store_external_refs table.

    Returns the Store linked to the given (provider, external_id) pair,
    or None if no match exists. This is checked BEFORE the slower
    address/name/proximity dedup in find_duplicate().

    Args:
        provider: The external provider name (e.g., "games_workshop").
        external_id: The provider-specific store identifier.
        session: Active SQLAlchemy session.

    Returns:
        The matched Store, or None.
    """
    assert isinstance(provider, str) and len(provider) > 0
    assert isinstance(external_id, str) and len(external_id) > 0

    stmt = (
        select(StoreExternalRef)
        .where(
            StoreExternalRef.provider == provider,
            StoreExternalRef.external_id == external_id,
        )
        .limit(1)
    )
    ref = session.execute(stmt).scalar_one_or_none()

    if ref is None:
        return None

    assert isinstance(ref, StoreExternalRef)

    store_stmt = select(Store).where(Store.id == ref.store_id).limit(1)
    store = session.execute(store_stmt).scalar_one_or_none()
    assert store is None or isinstance(store, Store)
    return store


def upsert_external_ref(
    store_id: UUID,
    provider: str,
    external_id: str,
    session: Session,
) -> StoreExternalRef:
    """Create or update an external ref linking a store to a provider ID.

    If the (provider, external_id) pair already exists, updates last_seen.
    Otherwise, inserts a new row.

    Args:
        store_id: UUID of the store.
        provider: The external provider name.
        external_id: The provider-specific store identifier.
        session: Active SQLAlchemy session.

    Returns:
        The StoreExternalRef (new or updated).
    """
    assert provider and len(provider) > 0
    assert external_id and len(external_id) > 0

    stmt = (
        select(StoreExternalRef)
        .where(
            StoreExternalRef.provider == provider,
            StoreExternalRef.external_id == external_id,
        )
        .limit(1)
    )
    existing = session.execute(stmt).scalar_one_or_none()

    if existing is not None:
        assert isinstance(existing, StoreExternalRef)
        existing.last_seen = datetime.now(tz=UTC)
        existing.store_id = store_id
        return existing

    ref = StoreExternalRef(
        store_id=store_id,
        provider=provider,
        external_id=external_id,
    )
    session.add(ref)
    assert ref.provider == provider
    return ref
