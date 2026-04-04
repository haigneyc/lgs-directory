"""Retro game store ingestion pipeline — delegates to shared ingest infrastructure."""

from __future__ import annotations

from sqlalchemy.orm import Session

from lgs_directory.discovery.ingest import IngestReport
from lgs_directory.discovery.ingest_base import ingest_stores
from lgs_directory.discovery.retro_games import RetroGameStoreRaw
from lgs_directory.models.enums import DiscoverySource


def ingest_retro_stores(
    raw_stores: list[RetroGameStoreRaw],
    session: Session,
    *,
    dry_run: bool = False,
) -> IngestReport:
    """Ingest retro game stores: validate -> normalize -> dedup -> insert/update.

    Automatically assigns the 'retro_games' category to new stores.

    Args:
        raw_stores: Parsed retro game store records.
        session: SQLAlchemy session (caller manages commit/rollback).
        dry_run: If True, compute stats without writing.

    Returns:
        IngestReport with counts.
    """
    assert isinstance(raw_stores, list)
    assert all(isinstance(s, RetroGameStoreRaw) for s in raw_stores)

    return ingest_stores(
        raw_stores=raw_stores,
        session=session,
        discovery_source=DiscoverySource.VIDEO_GAME_SAGE,
        provider_key="video_game_sage",
        label="retro store",
        get_external_id="source_id",
        dry_run=dry_run,
    )
