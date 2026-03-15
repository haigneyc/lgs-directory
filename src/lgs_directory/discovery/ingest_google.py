"""Google Places ingestion pipeline — normalize → dedup → insert."""

from __future__ import annotations

import logging
import re

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from lgs_directory.discovery.dedup import DeduplicationResult, find_duplicate
from lgs_directory.discovery.google_places import GooglePlaceRaw
from lgs_directory.discovery.ingest import IngestReport, _is_blocked_url
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

logger = logging.getLogger(__name__)

_BATCH_LOG_INTERVAL = 100

# Pattern for "City, State ZIP, Country" or "Street, City, State ZIP"
_GOOGLE_ADDRESS_RE = re.compile(
    r"^(?P<street>.+?),\s*(?P<city>[^,]+),\s*(?P<state>[A-Z]{2})\s+(?P<zip>\d{5}(?:-\d{4})?)"
)


def _parse_google_address(formatted_address: str) -> AddressSchema | None:
    """Parse Google's formatted address string into AddressSchema.

    Google format: "123 Main St, Portland, OR 97201, USA"
    Returns None if parsing fails.
    """
    assert isinstance(formatted_address, str), "address must be a string"

    match = _GOOGLE_ADDRESS_RE.match(formatted_address)
    if match is None:
        logger.debug("Could not parse Google address: %s", formatted_address)
        return None

    try:
        addr = AddressSchema(
            street=match.group("street").strip(),
            city=match.group("city").strip(),
            state=match.group("state").strip(),
            zip_code=match.group("zip").strip()[:5],
        )
    except ValidationError:
        logger.debug("Address validation failed for: %s", formatted_address)
        return None

    assert addr is not None
    return addr


def _create_store_from_google(raw: GooglePlaceRaw, addr: AddressSchema) -> Store:
    """Create a new Store from a Google Places record."""
    assert isinstance(raw, GooglePlaceRaw)
    assert isinstance(addr, AddressSchema)

    store = Store(
        name=raw.name,
        address=addr.model_dump(),
        latitude=raw.lat,
        longitude=raw.lng,
        phone=raw.phone,
        google_place_id=raw.place_id,
        status=StoreStatus.CANDIDATE,
        discovery_source=DiscoverySource.GOOGLE_PLACES,
    )

    # Seed OnlinePresence with website URL if available (skip WotC generic pages)
    if raw.website and not _is_blocked_url(raw.website):
        presence = OnlinePresence(
            channel_type=ChannelType.WEBSITE,
            url=raw.website,
            status=PresenceStatus.ACTIVE,
        )
        store.presences.append(presence)

    assert store.name == raw.name
    return store


def _update_store_from_google(store: Store, raw: GooglePlaceRaw) -> bool:
    """Update an existing store with Google data if it adds new info.

    Returns True if any fields were updated.
    """
    assert isinstance(store, Store)
    assert isinstance(raw, GooglePlaceRaw)

    updated = False

    if not store.google_place_id and raw.place_id:
        store.google_place_id = raw.place_id
        updated = True

    if store.latitude is None and raw.lat is not None:
        store.latitude = raw.lat
        updated = True

    if store.longitude is None and raw.lng is not None:
        store.longitude = raw.lng
        updated = True

    if not store.phone and raw.phone:
        store.phone = raw.phone
        updated = True

    return updated


def ingest_google_stores(
    raw_stores: list[GooglePlaceRaw],
    session: Session,
    *,
    dry_run: bool = False,
) -> IngestReport:
    """Ingest Google Places stores: parse → normalize → dedup → insert/update.

    Args:
        raw_stores: Parsed Google Places records.
        session: SQLAlchemy session (caller manages commit/rollback).
        dry_run: If True, compute stats without writing.

    Returns:
        IngestReport with counts.
    """
    assert isinstance(raw_stores, list)
    report = IngestReport(total=len(raw_stores))

    # Load existing stores once for dedup
    existing_stores: list[Store] = []
    if not dry_run:
        stmt = select(Store)
        existing_stores = list(session.execute(stmt).scalars().all())
        assert isinstance(existing_stores, list)
        logger.info("Loaded %d existing stores for deduplication", len(existing_stores))

    for i, raw in enumerate(raw_stores):
        assert isinstance(raw, GooglePlaceRaw)

        if (i + 1) % _BATCH_LOG_INTERVAL == 0:
            logger.info("Processing Google place %d / %d ...", i + 1, report.total)

        # 1. Parse address
        addr = _parse_google_address(raw.address)
        if addr is None:
            report.errors += 1
            report.error_details.append(
                f"Unparseable address for '{raw.name}' (place_id={raw.place_id}): "
                f"{raw.address}"
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

        # 3. Dedup
        dedup_result: DeduplicationResult = find_duplicate(
            candidate_name=raw.name,
            candidate_address=norm_addr,
            candidate_wpn_id=None,
            candidate_lat=raw.lat,
            candidate_lng=raw.lng,
            existing_stores=existing_stores,
            candidate_google_place_id=raw.place_id,
        )

        if dedup_result.needs_review:
            report.needs_review += 1

        if dedup_result.is_match:
            assert dedup_result.matched_store is not None
            was_updated = _update_store_from_google(dedup_result.matched_store, raw)
            if was_updated:
                report.updated += 1
            else:
                report.skipped += 1
        else:
            new_store = _create_store_from_google(raw, addr)
            session.add(new_store)
            session.flush()
            existing_stores.append(new_store)
            report.inserted += 1

    logger.info("%s", report)
    return report
