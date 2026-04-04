"""Comic store ingestion pipeline — delegates to shared ingest infrastructure."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from lgs_directory.discovery.comic_stores import ComicStoreRaw
from lgs_directory.discovery.ingest import IngestReport
from lgs_directory.discovery.ingest_base import ingest_stores
from lgs_directory.models.enums import DiscoverySource

_COMIC_SOURCE_CONFIG: dict[str, tuple[DiscoverySource, str]] = {
    "comicbookstores": (
        DiscoverySource.COMICBOOKSTORES,
        "comicbookstores",
    ),
    "league_comic_geeks": (
        DiscoverySource.LEAGUE_COMIC_GEEKS,
        "league_comic_geeks",
    ),
    "google_places": (
        DiscoverySource.GOOGLE_PLACES,
        "comicbookstores",
    ),
}


def ingest_comic_stores(
    raw_stores: list[ComicStoreRaw],
    session: Session,
    *,
    dry_run: bool = False,
) -> IngestReport:
    """Ingest comic stores: validate -> normalize -> dedup -> insert/update.

    Automatically assigns the 'comic_shop' category to new stores.

    Args:
        raw_stores: Parsed comic store records.
        session: SQLAlchemy session (caller manages commit/rollback).
        dry_run: If True, compute stats without writing.

    Returns:
        IngestReport with counts.
    """
    assert isinstance(raw_stores, list)
    assert all(isinstance(s, ComicStoreRaw) for s in raw_stores)

    grouped_raw_stores: dict[str, list[ComicStoreRaw]] = defaultdict(list)
    for raw_store in raw_stores:
        assert raw_store.source in _COMIC_SOURCE_CONFIG, (
            f"Unsupported comic source: {raw_store.source!r}"
        )
        grouped_raw_stores[raw_store.source].append(raw_store)

    combined_report = IngestReport(total=len(raw_stores))
    for source_key, source_stores in grouped_raw_stores.items():
        discovery_source, provider_key = _COMIC_SOURCE_CONFIG[source_key]
        report = ingest_stores(
            raw_stores=source_stores,
            session=session,
            discovery_source=discovery_source,
            provider_key=provider_key,
            label="comic store",
            get_external_id="source_id",
            dry_run=dry_run,
        )
        combined_report.inserted += report.inserted
        combined_report.updated += report.updated
        combined_report.skipped += report.skipped
        combined_report.errors += report.errors
        combined_report.needs_review += report.needs_review
        combined_report.error_details.extend(report.error_details)

    return combined_report
