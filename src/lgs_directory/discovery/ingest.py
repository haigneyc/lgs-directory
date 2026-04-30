"""Ingestion pipeline — orchestrates fetch → normalize → dedup → insert."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from urllib.parse import urlparse

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from lgs_directory.discovery.categories import assign_categories, get_default_categories
from lgs_directory.discovery.dedup import DeduplicationResult, find_duplicate
from lgs_directory.discovery.normalize import normalize_address
from lgs_directory.discovery.wpn import WpnStoreRaw
from lgs_directory.models.enums import (
    ChannelType,
    DiscoverySource,
    PresenceStatus,
    StoreStatus,
    WpnLevel,
)
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store
from lgs_directory.schemas import AddressSchema
from lgs_directory.slug import ensure_public_store_slug

logger = logging.getLogger(__name__)

_BATCH_LOG_INTERVAL = 100

_BLOCKED_URL_DOMAINS = {
    "wizards.com",
    "wpn.wizards.com",
    "magic.wizards.com",
    "locator.wizards.com",
}


def is_blocked_url(url: str) -> bool:
    """Check if URL belongs to a blocked domain (e.g., WotC generic pages)."""
    assert isinstance(url, str), "url must be a string"

    hostname = urlparse(url).hostname
    if hostname is None:
        return False

    hostname = hostname.lower()
    # Strip leading "www."
    if hostname.startswith("www."):
        hostname = hostname[4:]

    # Check hostname and all parent domains
    parts = hostname.split(".")
    for i in range(len(parts) - 1):
        candidate = ".".join(parts[i:])
        if candidate in _BLOCKED_URL_DOMAINS:
            return True

    return False


@dataclass
class IngestReport:
    """Summary of an ingestion run."""

    total: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    needs_review: int = 0
    error_details: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"Ingest complete: {self.total} processed — "
            f"{self.inserted} inserted, {self.updated} updated, "
            f"{self.skipped} skipped, {self.errors} errors, "
            f"{self.needs_review} need review"
        )


def _validate_address(raw: WpnStoreRaw) -> AddressSchema | None:
    """Validate a raw store's address through the AddressSchema.

    Returns None if validation fails.
    """
    assert isinstance(raw, WpnStoreRaw)
    state = raw.state.upper().strip()
    zip_code = raw.zip_code.strip()

    # Pad short ZIP codes
    if zip_code and len(zip_code) < 5:
        zip_code = zip_code.zfill(5)

    # Truncate ZIP+4 to 5
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


def _load_existing_stores(session: Session) -> list[Store]:
    """Load all existing stores from the database for dedup."""
    stmt = select(Store)
    stores = list(session.execute(stmt).scalars().all())
    assert isinstance(stores, list)
    logger.info("Loaded %d existing stores for deduplication", len(stores))
    return stores


def _create_store_from_raw(raw: WpnStoreRaw, addr: AddressSchema) -> Store:
    """Create a new Store ORM instance from raw WPN data."""
    assert isinstance(raw, WpnStoreRaw)
    assert isinstance(addr, AddressSchema)

    store = Store(
        name=raw.name,
        address=addr.model_dump(),
        latitude=raw.latitude,
        longitude=raw.longitude,
        phone=raw.phone,
        wpn_id=raw.wpn_id,
        wpn_level=WpnLevel.PREMIUM if raw.is_premium else WpnLevel.CORE,
        status=StoreStatus.CANDIDATE,
        discovery_source=DiscoverySource.WPN,
    )

    # Seed OnlinePresence with website URL if available (skip WotC generic pages)
    if raw.website and not is_blocked_url(raw.website):
        presence = OnlinePresence(
            channel_type=ChannelType.WEBSITE,
            url=raw.website,
            status=PresenceStatus.ACTIVE,
        )
        store.presences.append(presence)

    assert store.name == raw.name
    return store


def _update_store_from_raw(store: Store, raw: WpnStoreRaw) -> bool:
    """Update an existing store with WPN data if it adds new info.

    Returns True if any fields were updated.
    """
    assert isinstance(store, Store)
    assert isinstance(raw, WpnStoreRaw)

    updated = False

    if not store.wpn_id and raw.wpn_id:
        store.wpn_id = raw.wpn_id
        updated = True

    if not store.wpn_level:
        store.wpn_level = WpnLevel.PREMIUM if raw.is_premium else WpnLevel.CORE
        updated = True

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


def ingest_wpn_stores(
    raw_stores: list[WpnStoreRaw],
    session: Session,
    *,
    dry_run: bool = False,
) -> IngestReport:
    """Ingest WPN stores: validate → normalize → dedup → insert/update.

    Args:
        raw_stores: Parsed WPN store records.
        session: SQLAlchemy session (caller manages commit/rollback).
        dry_run: If True, compute stats without writing to the database.

    Returns:
        IngestReport with counts of inserted, updated, skipped, and errors.
    """
    assert isinstance(raw_stores, list)
    report = IngestReport(total=len(raw_stores))
    default_categories = get_default_categories(DiscoverySource.WPN)

    # Load existing stores once for dedup
    existing_stores = _load_existing_stores(session) if not dry_run else []

    for i, raw in enumerate(raw_stores):
        assert isinstance(raw, WpnStoreRaw)

        # Progress logging
        if (i + 1) % _BATCH_LOG_INTERVAL == 0:
            logger.info("Processing store %d / %d ...", i + 1, report.total)

        # 1. Validate address
        addr = _validate_address(raw)
        if addr is None:
            report.errors += 1
            report.error_details.append(
                f"Invalid address for '{raw.name}' (wpn_id={raw.wpn_id}): "
                f"{raw.street}, {raw.city}, {raw.state} {raw.zip_code}"
            )
            continue

        # 2. Normalize address for dedup
        try:
            norm_addr = normalize_address(
                street=addr.street,
                city=addr.city,
                state=addr.state,
                zip_code=addr.zip_code,
            )
        except (AssertionError, ValueError) as exc:
            report.errors += 1
            report.error_details.append(
                f"Normalization failed for '{raw.name}': {exc}"
            )
            continue

        if dry_run:
            report.inserted += 1
            continue

        # 3. Dedup against existing stores
        dedup_result: DeduplicationResult = find_duplicate(
            candidate_name=raw.name,
            candidate_address=norm_addr,
            candidate_wpn_id=raw.wpn_id,
            candidate_lat=raw.latitude,
            candidate_lng=raw.longitude,
            existing_stores=existing_stores,
        )

        if dedup_result.needs_review:
            report.needs_review += 1

        if dedup_result.is_match:
            assert dedup_result.matched_store is not None
            # Update existing store if we have new data
            matched_store = dedup_result.matched_store
            was_updated = _update_store_from_raw(matched_store, raw)
            slug_updated = ensure_public_store_slug(matched_store, session)
            if matched_store.id is not None:
                assign_categories(matched_store.id, default_categories, session)
            if was_updated or slug_updated:
                report.updated += 1
            else:
                report.skipped += 1
        else:
            # Insert new store
            new_store = _create_store_from_raw(raw, addr)
            ensure_public_store_slug(new_store, session)
            session.add(new_store)
            session.flush()
            existing_stores.append(new_store)
            if new_store.id is not None:
                assign_categories(new_store.id, default_categories, session)
            report.inserted += 1

    logger.info("%s", report)
    return report
