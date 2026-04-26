"""OSM Overpass ingestion pipeline — classify -> dedup -> insert/augment.

Runs after ``osm_overpass.OverpassClient`` returns a parsed candidate
list for one state. The pipeline:

1. classifies each candidate via ``classify_osm_candidate`` (3-tier);
2. dedups against existing stores using a 3-key strategy:
     a. ``store_external_refs`` lookup on (provider="osm", external_id);
     b. fuzzy name + 25 m geographic proximity (per spec §1.5);
     c. phone exact match OR website domain match;
3. for matches, augments the existing row with OSM enrichment but
   never overwrites Google-sourced canonical fields;
4. for new AUTO_ACCEPT candidates with complete addresses, inserts as
   CANDIDATE; new CANDIDATE_QUEUE candidates with complete addresses
   insert as PENDING_REVIEW (hidden from public site until promoted).
5. drops candidates without a complete address — Phase 1 keeps the
   ``stores.address`` non-null invariant (see migration
   ``d8c4f1a9b3e7``).
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from thefuzz import fuzz  # type: ignore[import-untyped]

from lgs_directory.discovery.categories import (
    assign_categories,
    get_default_categories,
)
from lgs_directory.discovery.dedup import (
    find_by_external_ref,
    upsert_external_ref,
)
from lgs_directory.discovery.ingest import is_blocked_url
from lgs_directory.discovery.normalize import normalize_address, normalize_name
from lgs_directory.discovery.osm_overpass import OsmPlaceRaw
from lgs_directory.discovery.quality_filters import (
    FilterTier,
    TierClassification,
    TierCounts,
    classify_osm_candidate,
)
from lgs_directory.models.enums import (
    ChannelType,
    DiscoverySource,
    PresenceStatus,
    StoreCategory,
    StoreStatus,
)
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store
from lgs_directory.models.store_external_ref import StoreExternalRef
from lgs_directory.schemas import AddressSchema

logger = logging.getLogger(__name__)

# OSM external ref provider name (matches the LFS branch convention).
OSM_PROVIDER = "osm"

# Dedup tuning — kept small so the bound-loop scan over existing stores
# is cheap. 25 m matches the spec §1.5 recommendation; fuzz>=85 mirrors
# ``dedup._FUZZY_NAME_THRESHOLD``.
_GEO_DEDUP_RADIUS_METERS = 25.0
_FUZZY_NAME_THRESHOLD = 85
_EARTH_RADIUS_METERS = 6_371_000.0

# Defensive bounds. Phase 1 ingests at most ~1k candidates per state,
# but we cap the loops anyway so a runaway response cannot freeze the
# CLI.
_MAX_INGEST_CANDIDATES = 50_000
_MAX_EXISTING_STORE_SCAN = 200_000

# Batch-progress logging cadence.
_BATCH_LOG_INTERVAL = 100

# US state codes — for AddressSchema validation. Mirrors LFS's
# ``ingest_osm._US_STATE_CODES``.
_US_STATE_CODES: frozenset[str] = frozenset([
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
    "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
    "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
    "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
])

_ZIP_PATTERN = re.compile(r"(\d{5})")
_PHONE_DIGITS = re.compile(r"\D+")


@dataclass
class OsmIngestReport:
    """Per-state OSM ingest summary."""

    state: str
    fetched: int = 0
    auto_accept: int = 0
    candidate_queue: int = 0
    auto_reject: int = 0
    inserted_candidate: int = 0
    inserted_pending_review: int = 0
    augmented_existing: int = 0
    skipped_no_change: int = 0
    skipped_no_address: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)
    sample_decisions: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"OSM[{self.state}] fetched={self.fetched} "
            f"accept={self.auto_accept} queue={self.candidate_queue} "
            f"reject={self.auto_reject} | "
            f"new_candidate={self.inserted_candidate} "
            f"new_pending_review={self.inserted_pending_review} "
            f"augmented={self.augmented_existing} "
            f"no_change={self.skipped_no_change} "
            f"no_address={self.skipped_no_address} "
            f"errors={self.errors}"
        )


def _parse_osm_address(raw: OsmPlaceRaw) -> AddressSchema | None:
    """Build AddressSchema from OSM ``addr:*`` tags or None when incomplete."""
    assert isinstance(raw, OsmPlaceRaw), "raw must be OsmPlaceRaw"

    street = (raw.street or "").strip()
    city = (raw.city or "").strip()
    state = (raw.state or "").strip().upper()
    postcode = (raw.postcode or "").strip()

    if not street or not city or not state or not postcode:
        return None

    if len(state) != 2 or state not in _US_STATE_CODES:
        return None

    zip_match = _ZIP_PATTERN.search(postcode)
    if zip_match is None:
        return None
    zip_code = zip_match.group(1)

    try:
        addr = AddressSchema(
            street=street[:255],
            city=city[:100],
            state=state,
            zip_code=zip_code,
        )
    except ValidationError:
        return None

    assert addr is not None
    return addr


def _normalize_phone(phone: str | None) -> str | None:
    """Reduce a phone number to just its digits for exact-match dedup."""
    if not phone:
        return None
    digits = _PHONE_DIGITS.sub("", phone)
    if len(digits) < 7:
        return None
    return digits


def _website_domain(url: str | None) -> str | None:
    """Return the apex hostname for an OSM ``website`` field."""
    if not url:
        return None
    parsed = urlparse(url if "://" in url else f"http://{url}")
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if not host or "." not in host:
        return None
    return host


def _haversine_meters(
    lat1: float, lon1: float, lat2: float, lon2: float,
) -> float:
    """Distance in meters between two lat/lng points."""
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
    return _EARTH_RADIUS_METERS * c


def _find_existing_match(
    raw: OsmPlaceRaw,
    existing_stores: list[Store],
    session: Session,
) -> Store | None:
    """3-key dedup: osm-id provider lookup, then geo+name fuzzy, then phone/domain."""
    assert isinstance(raw, OsmPlaceRaw)
    assert isinstance(existing_stores, list)

    # Key 1: deterministic store_external_refs lookup. Once a store has
    # an OSM external_ref this is O(1) for subsequent runs.
    osm_external_id = f"{raw.osm_type}/{raw.osm_id}"
    matched = find_by_external_ref(OSM_PROVIDER, osm_external_id, session)
    if matched is not None:
        return matched

    # Pre-compute candidate dedup keys
    candidate_norm_name = normalize_name(raw.name) if raw.name else ""
    candidate_phone = _normalize_phone(raw.phone)
    candidate_domain = _website_domain(raw.website)
    has_geo = raw.lat is not None and raw.lng is not None

    # Bound the scan defensively. Prod store count is ~6k; the cap is
    # for safety against runaway query results.
    scan_limit = min(len(existing_stores), _MAX_EXISTING_STORE_SCAN)

    # Key 2: fuzzy name + ~25 m geographic proximity
    if has_geo and candidate_norm_name:
        # Re-assert for type narrowing — the loop body relies on these.
        assert raw.lat is not None and raw.lng is not None
        cand_lat: float = raw.lat
        cand_lng: float = raw.lng
        for i in range(scan_limit):
            store = existing_stores[i]
            if store.latitude is None or store.longitude is None:
                continue
            dist = _haversine_meters(
                cand_lat, cand_lng, store.latitude, store.longitude,
            )
            if dist > _GEO_DEDUP_RADIUS_METERS:
                continue
            existing_norm = normalize_name(store.name)
            if not existing_norm:
                continue
            score = fuzz.token_set_ratio(candidate_norm_name, existing_norm)
            if score >= _FUZZY_NAME_THRESHOLD:
                return store

    # Key 3a: phone digit match
    if candidate_phone:
        for i in range(scan_limit):
            store = existing_stores[i]
            existing_phone = _normalize_phone(store.phone)
            if existing_phone is not None and existing_phone == candidate_phone:
                return store

    # Key 3b: website domain match against the store's presences
    if candidate_domain:
        for i in range(scan_limit):
            store = existing_stores[i]
            for presence in store.presences:
                if presence.channel_type != ChannelType.WEBSITE:
                    continue
                existing_domain = _website_domain(presence.url)
                if existing_domain is not None and existing_domain == candidate_domain:
                    return store

    return None


def _create_store_from_osm(
    raw: OsmPlaceRaw,
    addr: AddressSchema,
    initial_status: StoreStatus,
) -> Store:
    """Build a new Store from an OSM record. Caller adds to session and flushes."""
    assert isinstance(raw, OsmPlaceRaw)
    assert isinstance(addr, AddressSchema)
    assert isinstance(initial_status, StoreStatus)

    store = Store(
        name=raw.name,
        address=addr.model_dump(),
        latitude=raw.lat,
        longitude=raw.lng,
        phone=raw.phone,
        status=initial_status,
        discovery_source=DiscoverySource.OSM_OVERPASS,
    )

    if raw.website and not is_blocked_url(raw.website):
        presence = OnlinePresence(
            channel_type=ChannelType.WEBSITE,
            url=raw.website,
            status=PresenceStatus.ACTIVE,
        )
        store.presences.append(presence)

    assert store.name == raw.name
    return store


def _augment_existing_from_osm(store: Store, raw: OsmPlaceRaw) -> bool:
    """Augment an existing store with OSM enrichment without overwriting canonical fields.

    Per spec §1.5: latitude/longitude/phone are filled only if currently
    null; name/address/status/discovery_source are NEVER touched.
    Returns True iff any field was updated.
    """
    assert isinstance(store, Store)
    assert isinstance(raw, OsmPlaceRaw)

    updated = False

    if store.latitude is None and raw.lat is not None:
        store.latitude = raw.lat
        updated = True

    if store.longitude is None and raw.lng is not None:
        store.longitude = raw.lng
        updated = True

    if not store.phone and raw.phone:
        store.phone = raw.phone
        updated = True

    # If OSM contributes a website not already attached to the store,
    # add a new OnlinePresence row. Mirrors the LFS branch's behaviour.
    if raw.website and not is_blocked_url(raw.website):
        new_domain = _website_domain(raw.website)
        already_attached = False
        for presence in store.presences:
            if presence.channel_type != ChannelType.WEBSITE:
                continue
            if _website_domain(presence.url) == new_domain:
                already_attached = True
                break
        if not already_attached:
            store.presences.append(OnlinePresence(
                channel_type=ChannelType.WEBSITE,
                url=raw.website,
                status=PresenceStatus.ACTIVE,
            ))
            updated = True

    return updated


def _initial_status_for(tier: FilterTier) -> StoreStatus:
    """Map the classifier tier to the initial Store.status value."""
    assert isinstance(tier, FilterTier)
    if tier == FilterTier.AUTO_ACCEPT:
        return StoreStatus.CANDIDATE
    assert tier == FilterTier.CANDIDATE_QUEUE
    return StoreStatus.PENDING_REVIEW


def _load_existing_stores(session: Session) -> list[Store]:
    """Load all stores once for in-memory dedup. Mirrors ingest_base."""
    stmt = select(Store)
    stores = list(session.execute(stmt).scalars().all())
    assert isinstance(stores, list)
    logger.info("Loaded %d existing stores for OSM dedup", len(stores))
    return stores


def _record_sample(
    report: OsmIngestReport,
    raw: OsmPlaceRaw,
    classification: TierClassification,
    decision: str,
) -> None:
    """Record a per-candidate trace line for verbose CLI output."""
    if len(report.sample_decisions) >= 200:
        return
    report.sample_decisions.append(
        f"[{classification.tier.value}] {decision}: "
        f"name={raw.name!r} osm={raw.osm_type}/{raw.osm_id} "
        f"shop={raw.shop_type!r} reason={classification.reason}"
    )


def ingest_osm_state(
    state_code: str,
    raw_places: list[OsmPlaceRaw],
    session: Session,
    *,
    dry_run: bool = False,
) -> OsmIngestReport:
    """Run the OSM ingest for a single state's worth of candidates.

    Args:
        state_code: 2-letter US state code, used only for the report.
        raw_places: Parsed OSM candidates from ``OverpassClient.fetch_state``.
        session: Active SQLAlchemy session. Caller manages commit/rollback.
        dry_run: If True, classification + dedup run but no DB writes
            occur. Useful for the Colorado pilot's pre-flight check.
    """
    assert isinstance(state_code, str) and len(state_code) == 2
    assert isinstance(raw_places, list)
    assert isinstance(dry_run, bool)

    state_upper = state_code.upper()
    report = OsmIngestReport(state=state_upper, fetched=len(raw_places))
    tier_counts = TierCounts()
    default_categories = get_default_categories(DiscoverySource.OSM_OVERPASS)
    if not default_categories:
        # OSM is multi-category by nature; default to LGS until a
        # downstream classifier reassigns. ``StoreCategory.LGS`` value
        # is the same string the rest of the pipeline uses.
        default_categories = [StoreCategory.LGS.value]

    existing_stores: list[Store] = []
    if not dry_run:
        existing_stores = _load_existing_stores(session)

    cap = min(len(raw_places), _MAX_INGEST_CANDIDATES)
    for i in range(cap):
        raw = raw_places[i]
        assert isinstance(raw, OsmPlaceRaw)

        if (i + 1) % _BATCH_LOG_INTERVAL == 0:
            logger.info("OSM[%s]: processing %d / %d", state_upper, i + 1, cap)

        if not raw.name or not raw.name.strip():
            report.errors += 1
            report.error_details.append(
                f"empty name on osm_id={raw.osm_id} (skipped)"
            )
            continue

        classification = classify_osm_candidate(
            tags={"shop": raw.shop_type},
            name=raw.name,
        )
        tier_counts.record(classification.tier)
        if classification.tier == FilterTier.AUTO_ACCEPT:
            report.auto_accept += 1
        elif classification.tier == FilterTier.CANDIDATE_QUEUE:
            report.candidate_queue += 1
        else:
            report.auto_reject += 1
            _record_sample(report, raw, classification, "rejected")
            continue

        addr = _parse_osm_address(raw)
        if addr is None:
            report.skipped_no_address += 1
            _record_sample(report, raw, classification, "no_address")
            continue

        try:
            normalize_address(
                street=addr.street,
                city=addr.city,
                state=addr.state,
                zip_code=addr.zip_code,
            )
        except (AssertionError, ValueError) as exc:
            report.errors += 1
            report.error_details.append(
                f"normalize failed for '{raw.name}' (osm={raw.osm_id}): {exc}"
            )
            continue

        if dry_run:
            if classification.tier == FilterTier.AUTO_ACCEPT:
                report.inserted_candidate += 1
            else:
                report.inserted_pending_review += 1
            _record_sample(report, raw, classification, "dry_run_accept")
            continue

        # Live path: dedup + insert/augment
        matched = _find_existing_match(raw, existing_stores, session)
        osm_external_id = f"{raw.osm_type}/{raw.osm_id}"

        if matched is not None:
            was_updated = _augment_existing_from_osm(matched, raw)
            if matched.id is not None:
                upsert_external_ref(
                    matched.id, OSM_PROVIDER, osm_external_id, session,
                )
                if default_categories:
                    assign_categories(matched.id, default_categories, session)
            if was_updated:
                report.augmented_existing += 1
                _record_sample(report, raw, classification, "augmented")
            else:
                report.skipped_no_change += 1
                _record_sample(report, raw, classification, "match_no_change")
            continue

        initial_status = _initial_status_for(classification.tier)
        new_store = _create_store_from_osm(raw, addr, initial_status)
        session.add(new_store)
        session.flush()
        existing_stores.append(new_store)
        if new_store.id is not None:
            upsert_external_ref(
                new_store.id, OSM_PROVIDER, osm_external_id, session,
            )
            if default_categories:
                assign_categories(new_store.id, default_categories, session)

        if initial_status == StoreStatus.CANDIDATE:
            report.inserted_candidate += 1
            _record_sample(report, raw, classification, "inserted_candidate")
        else:
            report.inserted_pending_review += 1
            _record_sample(report, raw, classification, "inserted_pending_review")

    logger.info("%s | %s", report, tier_counts)
    return report


def list_pending_review_stores(
    session: Session, *, limit: int = 50,
) -> list[Store]:
    """Return up to ``limit`` PENDING_REVIEW stores ordered by first_seen ASC.

    Used by ``lgs discover review-queue`` so Chris/Vera can spot-check
    the OSM-derived backlog and either promote to CANDIDATE or close.
    """
    assert isinstance(limit, int) and limit > 0
    bounded_limit = min(limit, 1000)

    stmt = (
        select(Store)
        .where(Store.status == StoreStatus.PENDING_REVIEW)
        .order_by(Store.first_seen.asc())
        .limit(bounded_limit)
    )
    rows = list(session.execute(stmt).scalars().all())
    assert isinstance(rows, list)
    return rows


def find_osm_external_ref(store_id: str, session: Session) -> StoreExternalRef | None:
    """Helper for the review-queue CLI: fetch the OSM ref payload for a store, if any."""
    assert isinstance(store_id, str) and len(store_id) > 0

    stmt = (
        select(StoreExternalRef)
        .where(
            StoreExternalRef.provider == OSM_PROVIDER,
            StoreExternalRef.store_id == store_id,
        )
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()
