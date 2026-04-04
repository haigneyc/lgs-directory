"""Tests for comic ingestion source dispatch."""

from __future__ import annotations

from unittest.mock import MagicMock

from lgs_directory.discovery.comic_stores import ComicStoreRaw
from lgs_directory.discovery.ingest import IngestReport
from lgs_directory.discovery.ingest_comic import ingest_comic_stores
from lgs_directory.models.enums import DiscoverySource


def _make_comic_store(source: str) -> ComicStoreRaw:
    return ComicStoreRaw(
        source_id=f"{source}-1",
        source=source,
        name="Example Comics",
        street="123 Main St",
        city="Austin",
        state="TX",
        zip_code="78701",
    )


def test_ingest_comic_stores_dispatches_comicbookstores(monkeypatch) -> None:
    calls: list[tuple[DiscoverySource, str, int]] = []

    def fake_ingest_stores(**kwargs) -> IngestReport:  # type: ignore[no-untyped-def]
        calls.append(
            (
                kwargs["discovery_source"],
                kwargs["provider_key"],
                len(kwargs["raw_stores"]),
            )
        )
        return IngestReport(total=len(kwargs["raw_stores"]), inserted=len(kwargs["raw_stores"]))

    monkeypatch.setattr("lgs_directory.discovery.ingest_comic.ingest_stores", fake_ingest_stores)

    report = ingest_comic_stores(
        [_make_comic_store("comicbookstores")],
        MagicMock(),
    )

    assert calls == [(DiscoverySource.COMICBOOKSTORES, "comicbookstores", 1)]
    assert report.total == 1
    assert report.inserted == 1


def test_ingest_comic_stores_dispatches_each_source_group(monkeypatch) -> None:
    calls: list[tuple[DiscoverySource, str, int]] = []

    def fake_ingest_stores(**kwargs) -> IngestReport:  # type: ignore[no-untyped-def]
        calls.append(
            (
                kwargs["discovery_source"],
                kwargs["provider_key"],
                len(kwargs["raw_stores"]),
            )
        )
        return IngestReport(
            total=len(kwargs["raw_stores"]),
            inserted=0,
            updated=len(kwargs["raw_stores"]),
        )

    monkeypatch.setattr("lgs_directory.discovery.ingest_comic.ingest_stores", fake_ingest_stores)

    report = ingest_comic_stores(
        [
            _make_comic_store("league_comic_geeks"),
            _make_comic_store("comicbookstores"),
        ],
        MagicMock(),
    )

    assert sorted(calls) == sorted(
        [
            (DiscoverySource.LEAGUE_COMIC_GEEKS, "league_comic_geeks", 1),
            (DiscoverySource.COMICBOOKSTORES, "comicbookstores", 1),
        ]
    )
    assert report.total == 2
    assert report.updated == 2
