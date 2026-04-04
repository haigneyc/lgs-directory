"""Tests for the comic store scraper — parsing, cache round-trip."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lgs_directory.discovery.comic_stores import (
    ComicStoreRaw,
    _parse_cbs_store,
    _parse_lcg_store,
    load_raw_from_cache,
    save_raw_to_cache,
)


def _make_lcg_data(
    store_id: str = "lcg-100",
    name: str = "Cosmic Comics",
    street: str = "50 Comic Blvd",
    city: str = "Chicago",
    state: str = "IL",
    zip_code: str = "60601",
) -> dict[str, Any]:
    """Build a minimal LCG store dict."""
    return {
        "id": store_id,
        "name": name,
        "address": {
            "street": street,
            "city": city,
            "state": state,
            "zip": zip_code,
        },
        "phone": "312-555-0100",
        "website": "https://cosmiccomics.com",
        "latitude": 41.8781,
        "longitude": -87.6298,
    }


def _make_cbs_data(
    store_id: str = "cbs-200",
    name: str = "Hero Haven",
    street: str = "75 Hero St",
    city: str = "Denver",
    state: str = "CO",
    zip_code: str = "80202",
) -> dict[str, Any]:
    """Build a minimal comicbookstores.co store dict."""
    return {
        "id": store_id,
        "name": name,
        "street": street,
        "city": city,
        "state": state,
        "zip": zip_code,
        "phone": "303-555-0100",
        "website": "https://herohaven.com",
        "lat": 39.7392,
        "lng": -104.9903,
    }


class TestParseLcgStore:
    """Tests for _parse_lcg_store."""

    def test_full_store(self) -> None:
        data = _make_lcg_data()
        result = _parse_lcg_store(data)
        assert result is not None
        assert result.source_id == "lcg-100"
        assert result.source == "league_comic_geeks"
        assert result.name == "Cosmic Comics"

    def test_missing_name_returns_none(self) -> None:
        data = _make_lcg_data(name="")
        result = _parse_lcg_store(data)
        assert result is None

    def test_missing_id_returns_none(self) -> None:
        data = _make_lcg_data(store_id="")
        result = _parse_lcg_store(data)
        assert result is None

    def test_missing_street_returns_none(self) -> None:
        data = _make_lcg_data(street="")
        result = _parse_lcg_store(data)
        assert result is None

    def test_flat_address_string_returns_none(self) -> None:
        data = {"id": "lcg-100", "name": "Store", "address": "123 Main St, Chicago, IL"}
        result = _parse_lcg_store(data)
        assert result is None


class TestParseCbsStore:
    """Tests for _parse_cbs_store."""

    def test_full_store(self) -> None:
        data = _make_cbs_data()
        result = _parse_cbs_store(data)
        assert result is not None
        assert result.source_id == "cbs-200"
        assert result.source == "comicbookstores"
        assert result.name == "Hero Haven"

    def test_missing_name_returns_none(self) -> None:
        data = _make_cbs_data(name="")
        result = _parse_cbs_store(data)
        assert result is None

    def test_missing_city_returns_none(self) -> None:
        data = _make_cbs_data(city="")
        result = _parse_cbs_store(data)
        assert result is None


class TestComicCacheRoundTrip:
    """Tests for save/load cache functions."""

    def test_round_trip(self, tmp_path: Path) -> None:
        stores = [
            ComicStoreRaw(
                source_id="lcg-1",
                source="league_comic_geeks",
                name="Comics R Us",
                street="1 Main St",
                city="Portland",
                state="OR",
                zip_code="97201",
            ),
        ]
        cache_path = tmp_path / "comic_cache.json"
        save_raw_to_cache(stores, cache_path)
        loaded = load_raw_from_cache(cache_path)
        assert len(loaded) == 1
        assert loaded[0].source_id == "lcg-1"

    def test_load_nonexistent_raises(self, tmp_path: Path) -> None:
        with pytest.raises(AssertionError, match="Cache file not found"):
            load_raw_from_cache(tmp_path / "missing.json")

    def test_cache_is_valid_json(self, tmp_path: Path) -> None:
        stores = [
            ComicStoreRaw(
                source_id="cbs-1",
                source="comicbookstores",
                name="Hero Shop",
                street="2 Oak Ave",
                city="Seattle",
                state="WA",
                zip_code="98101",
            ),
        ]
        cache_path = tmp_path / "comic_cache.json"
        save_raw_to_cache(stores, cache_path)
        data = json.loads(cache_path.read_text())
        assert isinstance(data, list)
        assert len(data) == 1
