"""Re-crawl diffing — detect new and delisted stores via discovery re-runs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from lgs_directory.models.enums import CheckType
from lgs_directory.models.store import Store
from lgs_directory.models.validation_log import ValidationLog

logger = logging.getLogger(__name__)


@dataclass
class RecrawlReport:
    """Summary of a re-crawl diff run."""

    new_stores: int = 0
    delisted_store_ids: list[UUID] = field(default_factory=list)
    updated: int = 0
    unchanged: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)

    @property
    def delisted(self) -> int:
        return len(self.delisted_store_ids)

    def __str__(self) -> str:
        return (
            f"Recrawl complete: {self.new_stores} new, "
            f"{self.delisted} delisted, "
            f"{self.updated} updated, "
            f"{self.unchanged} unchanged, "
            f"{self.errors} errors"
        )


def recrawl_wpn_with_diff(
    session: Session,
    raw_stores: list,
    *,
    dry_run: bool = False,
) -> RecrawlReport:
    """Run WPN ingestion and diff against existing stores.

    Expects pre-fetched raw_stores (caller handles fetch/cache).
    Compares wpn_id values before and after ingest to detect new
    and delisted stores.

    Args:
        session: SQLAlchemy session.
        raw_stores: List of WpnStoreRaw records (already fetched).
        dry_run: If True, compute diff without writing.

    Returns:
        RecrawlReport with new/delisted/updated counts.
    """
    assert session is not None, "Session must not be None"
    assert isinstance(raw_stores, list)

    from lgs_directory.discovery.ingest import ingest_wpn_stores

    report = RecrawlReport()

    # Snapshot existing WPN IDs
    stmt = (
        select(Store.id, Store.wpn_id)
        .where(Store.wpn_id.isnot(None))
    )
    existing_rows = list(session.execute(stmt).all())
    existing_wpn_ids = {row.wpn_id for row in existing_rows}
    wpn_id_to_store_id = {row.wpn_id: row.id for row in existing_rows}
    assert isinstance(existing_wpn_ids, set)

    logger.info("Snapshot: %d existing WPN stores", len(existing_wpn_ids))

    # Collect incoming WPN IDs
    incoming_wpn_ids = {r.wpn_id for r in raw_stores if r.wpn_id}

    # Detect delistings (in DB but not in new crawl)
    delisted_wpn_ids = existing_wpn_ids - incoming_wpn_ids
    for wpn_id in delisted_wpn_ids:
        store_id = wpn_id_to_store_id.get(wpn_id)
        if store_id is not None:
            report.delisted_store_ids.append(store_id)

            if not dry_run:
                # Log delisting signal
                log = ValidationLog(
                    store_id=store_id,
                    check_type=CheckType.CLOSURE_DETECT,
                    result={
                        "reason": "absent_from_wpn_recrawl",
                        "wpn_id": wpn_id,
                    },
                )
                session.add(log)

    logger.info("Detected %d WPN delistings", len(delisted_wpn_ids))

    # Run ingest to pick up new + updated stores
    if not dry_run:
        ingest_report = ingest_wpn_stores(raw_stores, session)
        report.new_stores = ingest_report.inserted
        report.updated = ingest_report.updated
        report.unchanged = ingest_report.skipped
        report.errors = ingest_report.errors
        report.error_details = ingest_report.error_details
    else:
        # In dry-run, compute new IDs
        new_wpn_ids = incoming_wpn_ids - existing_wpn_ids
        report.new_stores = len(new_wpn_ids)
        report.unchanged = len(incoming_wpn_ids & existing_wpn_ids)

    logger.info("%s", report)
    return report


def recrawl_google_with_diff(
    session: Session,
    raw_stores: list,
    *,
    dry_run: bool = False,
    allow_delistings: bool = True,
) -> RecrawlReport:
    """Run Google Places ingestion and diff against existing stores.

    Expects pre-fetched raw_stores (caller handles fetch/cache).
    Compares google_place_id values before and after ingest.

    Args:
        session: SQLAlchemy session.
        raw_stores: List of GooglePlaceRaw records (already fetched).
        dry_run: If True, compute diff without writing.
        allow_delistings: If True, treat the incoming set as a complete Google crawl
            and compute delistings. Disable this for sharded or request-capped scans.

    Returns:
        RecrawlReport with new/delisted/updated counts.
    """
    assert session is not None, "Session must not be None"
    assert isinstance(raw_stores, list)

    from lgs_directory.discovery.ingest_google import ingest_google_stores

    report = RecrawlReport()

    # Snapshot existing Google Place IDs
    stmt = (
        select(Store.id, Store.google_place_id)
        .where(Store.google_place_id.isnot(None))
    )
    existing_rows = list(session.execute(stmt).all())
    existing_place_ids = {row.google_place_id for row in existing_rows}
    place_id_to_store_id = {row.google_place_id: row.id for row in existing_rows}
    assert isinstance(existing_place_ids, set)

    logger.info("Snapshot: %d existing Google Places stores", len(existing_place_ids))

    # Collect incoming place IDs
    incoming_place_ids = {r.place_id for r in raw_stores if r.place_id}

    delisted_place_ids: set[str] = set()
    if allow_delistings:
        delisted_place_ids = existing_place_ids - incoming_place_ids
        for place_id in delisted_place_ids:
            store_id = place_id_to_store_id.get(place_id)
            if store_id is not None:
                report.delisted_store_ids.append(store_id)

                if not dry_run:
                    log = ValidationLog(
                        store_id=store_id,
                        check_type=CheckType.CLOSURE_DETECT,
                        result={
                            "reason": "absent_from_google_recrawl",
                            "google_place_id": place_id,
                        },
                    )
                    session.add(log)

        logger.info("Detected %d Google Places delistings", len(delisted_place_ids))
    else:
        logger.info(
            "Skipping Google Places delisting detection because this recrawl is partial",
        )

    # Run ingest
    if not dry_run:
        ingest_report = ingest_google_stores(raw_stores, session)
        report.new_stores = ingest_report.inserted
        report.updated = ingest_report.updated
        report.unchanged = ingest_report.skipped
        report.errors = ingest_report.errors
        report.error_details = ingest_report.error_details
    else:
        new_place_ids = incoming_place_ids - existing_place_ids
        report.new_stores = len(new_place_ids)
        report.unchanged = len(incoming_place_ids & existing_place_ids)

    logger.info("%s", report)
    return report
