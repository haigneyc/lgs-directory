"""Shared ingestion pipeline infrastructure for source-specific ingest modules.

Extracts the common validate -> normalize -> dedup -> insert/update pattern
used by comic, Games Workshop, and retro game store ingestion.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Protocol

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from lgs_directory.discovery.categories import assign_categories, get_default_categories
from lgs_directory.discovery.dedup import (
    DeduplicationResult,
    find_by_external_ref,
    find_duplicate,
    upsert_external_ref,
)
from lgs_directory.discovery.ingest import IngestReport, is_blocked_url
from lgs_directory.discovery.normalize import normalize_address
from lgs_directory.models.enums import (
    ChannelType,
    DiscoverySource,
    PresenceStatus,
    StoreStatus,
)
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store
from lgs_directory.schemas import AddressSchema
from lgs_directory.slug import ensure_public_store_slug

logger = logging.getLogger(__name__)

_BATCH_LOG_INTERVAL = 100


class RawStoreRecord(Protocol):
    """Protocol for raw store records from any discovery source.

    All source-specific raw models (ComicStoreRaw, GamesWorkshopStoreRaw,
    RetroGameStoreRaw) satisfy this protocol.
    """

    name: str
    street: str
    city: str
    state: str
    zip_code: str
    phone: str | None
    website: str | None
    latitude: float | None
    longitude: float | None


def validate_raw_address(raw: RawStoreRecord) -> AddressSchema | None:
    """Validate a raw store's address through AddressSchema.

    Returns None if validation fails. Shared by all source-specific pipelines.
    """
    assert hasattr(raw, "name"), "raw must have a name attribute"
    assert hasattr(raw, "state"), "raw must have a state attribute"

    state = raw.state.upper().strip()
    zip_code = raw.zip_code.strip()

    if zip_code and len(zip_code) < 5:
        zip_code = zip_code.zfill(5)

    if "-" in zip_code:
        zip_code = zip_code.split("-")[0]

    try:
        addr = AddressSchema(
            street=raw.street.strip(),
            city=raw.city.strip(),
            state=state[:2] if len(state) >= 2 else state,
            zip_code=zip_code,
        )
    except ValidationError:
        return None

    assert addr is not None
    return addr


def create_store_from_raw(
    raw: RawStoreRecord,
    addr: AddressSchema,
    discovery_source: DiscoverySource,
) -> Store:
    """Create a new Store from a raw store record.

    Args:
        raw: The raw store record (any source).
        addr: Validated address schema.
        discovery_source: The DiscoverySource enum value for this pipeline.

    Returns:
        A new Store ORM instance (not yet added to the session).
    """
    assert hasattr(raw, "name"), "raw must have a name attribute"
    assert isinstance(addr, AddressSchema)

    store = Store(
        name=raw.name,
        address=addr.model_dump(),
        latitude=raw.latitude,
        longitude=raw.longitude,
        phone=raw.phone,
        status=StoreStatus.CANDIDATE,
        discovery_source=discovery_source,
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


def update_store_from_raw(store: Store, raw: RawStoreRecord) -> bool:
    """Update an existing store with new data if it adds new info.

    Returns True if any fields were updated.
    """
    assert isinstance(store, Store)
    assert hasattr(raw, "name"), "raw must have a name attribute"

    updated = False

    if store.latitude is None and raw.latitude is not None:
        store.latitude = raw.latitude
        updated = True

    if store.longitude is None and raw.longitude is not None:
        store.longitude = raw.longitude
        updated = True

    if not store.phone and raw.phone:
        store.phone = raw.phone
        updated = True

    return updated


def ingest_stores(
    raw_stores: Sequence[RawStoreRecord],
    session: Session,
    discovery_source: DiscoverySource,
    provider_key: str,
    label: str,
    get_external_id: str,
    *,
    dry_run: bool = False,
) -> IngestReport:
    """Generic ingestion pipeline: validate -> normalize -> dedup -> insert/update.

    This function extracts the shared pattern from ingest_comic_stores,
    ingest_gw_stores, and ingest_retro_stores.

    Args:
        raw_stores: List of raw store records (any source).
        session: SQLAlchemy session (caller manages commit/rollback).
        discovery_source: The DiscoverySource enum value.
        provider_key: Key for get_default_categories() lookup.
        label: Human-readable label for log messages (e.g., "comic store").
        get_external_id: Attribute name on the raw model for the external ID
            (e.g., "source_id", "gw_id").
        dry_run: If True, compute stats without writing.

    Returns:
        IngestReport with counts.
    """
    assert hasattr(raw_stores, "__len__"), "raw_stores must be a sized sequence"
    assert isinstance(provider_key, str) and len(provider_key) > 0

    # Fail fast: verify the external ID attribute exists on the raw model
    if len(raw_stores) > 0:
        assert hasattr(raw_stores[0], get_external_id), (
            f"Raw store model missing attribute {get_external_id!r}. "
            f"Check the get_external_id parameter passed to ingest_stores()."
        )

    report = IngestReport(total=len(raw_stores))

    existing_stores: list[Store] = []
    if not dry_run:
        # NOTE: Known scaling concern -- full table load for dedup. At 50k+ stores,
        # consider deduplicating against the database directly (query by
        # normalized address/name) instead of loading all stores into memory.
        # See: store-expansion-phase2-review.md concern #3.
        # TODO(scaling): Now used by 3+ source pipelines (wpn, gw, comics, retro).
        # When store count exceeds ~20K, refactor to query-based dedup (e.g., DB
        # lookup by normalized address/zip) instead of full table load.
        # Tracked: store-expansion-phase4-review.md concern #2.
        stmt = select(Store)
        existing_stores = list(session.execute(stmt).scalars().all())
        assert isinstance(existing_stores, list)
        logger.info("Loaded %d existing stores for deduplication", len(existing_stores))

    default_cats = get_default_categories(provider_key)
    assert isinstance(default_cats, list)

    for i, raw in enumerate(raw_stores):
        if (i + 1) % _BATCH_LOG_INTERVAL == 0:
            logger.info("Processing %s %d / %d ...", label, i + 1, report.total)

        # 1. Validate address
        addr = validate_raw_address(raw)
        if addr is None:
            ext_id = getattr(raw, get_external_id, "unknown")
            report.errors += 1
            report.error_details.append(
                f"Invalid address for '{raw.name}' ({get_external_id}={ext_id}): "
                f"{raw.street}, {raw.city}, {raw.state} {raw.zip_code}"
            )
            continue

        # 2. Normalize for dedup
        try:
            norm_addr = normalize_address(
                street=addr.street,
                city=addr.city,
                state=addr.state,
                zip_code=addr.zip_code,
            )
        except (AssertionError, ValueError) as exc:
            report.errors += 1
            report.error_details.append(f"Normalization failed for '{raw.name}': {exc}")
            continue

        if dry_run:
            report.inserted += 1
            continue

        # 3. Cross-source dedup: fast exact-match via store_external_refs
        ext_id = getattr(raw, get_external_id, None)
        matched_store: Store | None = None

        if ext_id is not None:
            matched_store = find_by_external_ref(provider_key, str(ext_id), session)

        # 4. Fall through to address/name/proximity dedup if no external ref match
        if matched_store is None:
            dedup_result: DeduplicationResult = find_duplicate(
                candidate_name=raw.name,
                candidate_address=norm_addr,
                candidate_wpn_id=None,
                candidate_lat=raw.latitude,
                candidate_lng=raw.longitude,
                existing_stores=existing_stores,
            )

            if dedup_result.needs_review:
                report.needs_review += 1

            if dedup_result.is_match:
                assert dedup_result.matched_store is not None
                matched_store = dedup_result.matched_store

        if matched_store is not None:
            was_updated = update_store_from_raw(matched_store, raw)
            slug_updated = ensure_public_store_slug(matched_store, session)
            if was_updated or slug_updated:
                report.updated += 1
            else:
                report.skipped += 1
            # Accumulate categories from this source onto the matched store
            if default_cats and matched_store.id is not None:
                assign_categories(matched_store.id, default_cats, session)
            # Track external ref for future cross-source lookups
            if ext_id is not None and matched_store.id is not None:
                upsert_external_ref(matched_store.id, provider_key, str(ext_id), session)
        else:
            new_store = create_store_from_raw(raw, addr, discovery_source)
            ensure_public_store_slug(new_store, session)
            session.add(new_store)
            session.flush()
            existing_stores.append(new_store)
            report.inserted += 1
            if default_cats and new_store.id is not None:
                assign_categories(new_store.id, default_cats, session)
            # Record external ref for the new store
            if ext_id is not None and new_store.id is not None:
                upsert_external_ref(new_store.id, provider_key, str(ext_id), session)

    logger.info("%s", report)
    return report
