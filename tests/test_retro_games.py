"""Tests for the retro game store scraper — parsing, cache round-trip."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lgs_directory.discovery.retro_games import (
    RetroGameStoreRaw,
    _parse_racketboy_store,
    _parse_vgs_store,
    load_raw_from_cache,
    save_raw_to_cache,
)


def _make_vgs_data(
    store_id: str = "vgs-100",
    name: str = "Retro Replay",
    street: str = "42 Pixel Way",
    city: str = "Nashville",
    state: str = "TN",
    zip_code: str = "37201",
) -> dict[str, Any]:
    """Build a minimal Video Game Sage store dict."""
    return {
        "id": store_id,
        "name": name,
        "street": street,
        "city": city,
        "state": state,
        "zip": zip_code,
        "phone": "615-555-0100",
        "website": "https://retroreplay.com",
        "lat": 36.1627,
        "lng": -86.7816,
    }


def _make_racketboy_data(
    store_id: str = "rb-200",
    name: str = "8-Bit Emporium",
    street: str = "88 Cartridge Ct",
    city: str = "Phoenix",
    state: str = "AZ",
    zip_code: str = "85001",
) -> dict[str, Any]:
    """Build a minimal Racketboy store dict."""
    return {
        "id": store_id,
        "name": name,
        "street": street,
        "city": city,
        "state": state,
        "zip": zip_code,
        "phone": "602-555-0100",
        "website": "https://8bitemporium.com",
        "lat": 33.4484,
        "lng": -112.0740,
    }


class TestParseVgsStore:
    """Tests for _parse_vgs_store."""

    def test_full_store(self) -> None:
        data = _make_vgs_data()
        result = _parse_vgs_store(data)
        assert result is not None
        assert result.source_id == "vgs-100"
        assert result.source == "video_game_sage"
        assert result.name == "Retro Replay"

    def test_missing_name_returns_none(self) -> None:
        data = _make_vgs_data(name="")
        result = _parse_vgs_store(data)
        assert result is None

    def test_missing_id_returns_none(self) -> None:
        data = _make_vgs_data(store_id="")
        result = _parse_vgs_store(data)
        assert result is None

    def test_missing_street_returns_none(self) -> None:
        data = _make_vgs_data(street="")
        result = _parse_vgs_store(data)
        assert result is None

    def test_missing_city_returns_none(self) -> None:
        data = _make_vgs_data(city="")
        result = _parse_vgs_store(data)
        assert result is None

    def test_optional_fields_default_none(self) -> None:
        data = {
            "id": "vgs-456", "name": "Mini Retro",
            "street": "1 St", "city": "LA", "state": "CA", "zip": "90001",
        }
        result = _parse_vgs_store(data)
        assert result is not None
        assert result.phone is None
        assert result.website is None


class TestParseRacketboyStore:
    """Tests for _parse_racketboy_store."""

    def test_full_store(self) -> None:
        data = _make_racketboy_data()
        result = _parse_racketboy_store(data)
        assert result is not None
        assert result.source_id == "rb-200"
        assert result.source == "racketboy"
        assert result.name == "8-Bit Emporium"

    def test_missing_name_returns_none(self) -> None:
        data = _make_racketboy_data(name="")
        result = _parse_racketboy_store(data)
        assert result is None

    def test_missing_street_returns_none(self) -> None:
        data = _make_racketboy_data(street="")
        result = _parse_racketboy_store(data)
        assert result is None


class TestRetroCacheRoundTrip:
    """Tests for save/load cache functions."""

    def test_round_trip(self, tmp_path: Path) -> None:
        stores = [
            RetroGameStoreRaw(
                source_id="vgs-1",
                source="video_game_sage",
                name="Retro Zone",
                street="1 Main St",
                city="Portland",
                state="OR",
                zip_code="97201",
            ),
        ]
        cache_path = tmp_path / "retro_cache.json"
        save_raw_to_cache(stores, cache_path)
        loaded = load_raw_from_cache(cache_path)
        assert len(loaded) == 1
        assert loaded[0].source_id == "vgs-1"

    def test_load_nonexistent_raises(self, tmp_path: Path) -> None:
        with pytest.raises(AssertionError, match="Cache file not found"):
            load_raw_from_cache(tmp_path / "missing.json")

    def test_cache_is_valid_json(self, tmp_path: Path) -> None:
        stores = [
            RetroGameStoreRaw(
                source_id="rb-1",
                source="racketboy",
                name="Cart Kings",
                street="2 Oak Ave",
                city="Seattle",
                state="WA",
                zip_code="98101",
            ),
        ]
        cache_path = tmp_path / "retro_cache.json"
        save_raw_to_cache(stores, cache_path)
        data = json.loads(cache_path.read_text())
        assert isinstance(data, list)
        assert len(data) == 1
