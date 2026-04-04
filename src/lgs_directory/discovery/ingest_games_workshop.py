"""Games Workshop ingestion pipeline — delegates to shared ingest infrastructure."""

from __future__ import annotations

from sqlalchemy.orm import Session

from lgs_directory.discovery.games_workshop import GamesWorkshopStoreRaw
from lgs_directory.discovery.ingest import IngestReport
from lgs_directory.discovery.ingest_base import ingest_stores
from lgs_directory.models.enums import DiscoverySource


def ingest_gw_stores(
    raw_stores: list[GamesWorkshopStoreRaw],
    session: Session,
    *,
    dry_run: bool = False,
) -> IngestReport:
    """Ingest Games Workshop stores: validate -> normalize -> dedup -> insert/update.

    Automatically assigns the 'hobby_miniatures' category to new stores.

    Args:
        raw_stores: Parsed GW store records.
        session: SQLAlchemy session (caller manages commit/rollback).
        dry_run: If True, compute stats without writing.

    Returns:
        IngestReport with counts.
    """
    assert isinstance(raw_stores, list)
    assert all(isinstance(s, GamesWorkshopStoreRaw) for s in raw_stores)

    return ingest_stores(
        raw_stores=raw_stores,
        session=session,
        discovery_source=DiscoverySource.GAMES_WORKSHOP,
        provider_key="games_workshop",
        label="GW store",
        get_external_id="gw_id",
        dry_run=dry_run,
    )
