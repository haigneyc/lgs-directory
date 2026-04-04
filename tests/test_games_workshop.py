"""Tests for the Games Workshop scraper — parsing, cache round-trip."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lgs_directory.discovery.games_workshop import (
    GamesWorkshopStoreRaw,
    _parse_gw_store,
    load_raw_from_cache,
    save_raw_to_cache,
)


def _make_gw_data(
    store_id: str = "gw-123",
    name: str = "Warp Charge Games",
    street: str = "100 Hobby Ln",
    city: str = "Austin",
    state: str = "TX",
    zip_code: str = "78701",
) -> dict[str, Any]:
    """Build a minimal GW store API response dict."""
    return {
        "id": store_id,
        "name": name,
        "address": {
            "line1": street,
            "town": city,
            "region": state,
            "postalCode": zip_code,
            "country": "US",
        },
        "phone": "512-555-0100",
        "website": "https://warpchargegames.com",
        "latitude": 30.2672,
        "longitude": -97.7431,
        "storeType": "Independent Retailer",
    }


class TestParseGwStore:
    """Tests for _parse_gw_store."""

    def test_full_store(self) -> None:
        data = _make_gw_data()
        result = _parse_gw_store(data)
        assert result is not None
        assert result.gw_id == "gw-123"
        assert result.name == "Warp Charge Games"
        assert result.street == "100 Hobby Ln"
        assert result.city == "Austin"
        assert result.state == "TX"

    def test_missing_name_returns_none(self) -> None:
        data = _make_gw_data(name="")
        result = _parse_gw_store(data)
        assert result is None

    def test_missing_id_returns_none(self) -> None:
        data = _make_gw_data(store_id="")
        result = _parse_gw_store(data)
        assert result is None

    def test_missing_street_returns_none(self) -> None:
        data = _make_gw_data(street="")
        result = _parse_gw_store(data)
        assert result is None

    def test_missing_city_returns_none(self) -> None:
        data = _make_gw_data(city="")
        result = _parse_gw_store(data)
        assert result is None

    def test_optional_fields_default_none(self) -> None:
        data = {
            "id": "gw-456",
            "name": "Mini Store",
            "address": {
                "line1": "200 Paint St",
                "town": "Denver",
                "region": "CO",
                "postalCode": "80202",
                "country": "US",
            },
        }
        result = _parse_gw_store(data)
        assert result is not None
        assert result.phone is None
        assert result.website is None
        assert result.latitude is None

    def test_non_dict_address_returns_none(self) -> None:
        data = {
            "id": "gw-789",
            "name": "Some Store",
            "address": "123 Main St, Denver, CO 80202",
        }
        result = _parse_gw_store(data)
        assert result is None

class TestCacheRoundTrip:
    """Tests for save/load cache functions."""

    def test_round_trip(self, tmp_path: Path) -> None:
        stores = [
            GamesWorkshopStoreRaw(
                gw_id="gw-1",
                name="Store A",
                street="1 Main St",
                city="Portland",
                state="OR",
                zip_code="97201",
                country="US",
            ),
            GamesWorkshopStoreRaw(
                gw_id="gw-2",
                name="Store B",
                street="2 Oak Ave",
                city="Seattle",
                state="WA",
                zip_code="98101",
                country="US",
            ),
        ]
        cache_path = tmp_path / "gw_cache.json"
        save_raw_to_cache(stores, cache_path)
        loaded = load_raw_from_cache(cache_path)
        assert len(loaded) == 2
        assert loaded[0].gw_id == "gw-1"
        assert loaded[1].name == "Store B"

    def test_load_nonexistent_raises(self, tmp_path: Path) -> None:
        with pytest.raises(AssertionError, match="Cache file not found"):
            load_raw_from_cache(tmp_path / "missing.json")

    def test_cache_is_valid_json(self, tmp_path: Path) -> None:
        stores = [
            GamesWorkshopStoreRaw(
                gw_id="gw-1",
                name="Store A",
                street="1 Main St",
                city="Portland",
                state="OR",
                zip_code="97201",
                country="US",
            ),
        ]
        cache_path = tmp_path / "gw_cache.json"
        save_raw_to_cache(stores, cache_path)
        data = json.loads(cache_path.read_text())
        assert isinstance(data, list)
        assert len(data) == 1
