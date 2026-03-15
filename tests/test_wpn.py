"""Tests for the WPN scraper — uses fixtures, no live API calls."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lgs_directory.discovery.wpn import (
    WpnStoreRaw,
    _api_store_to_raw,
    _parse_postal_address,
    load_raw_from_cache,
    save_raw_to_cache,
)

# --- Fixtures ---

SAMPLE_API_STORE: dict[str, object] = {
    "id": "18077",
    "name": "Tabletop Village",
    "postalAddress": "616 8th Ave S, Seattle, WA, 98104, United States",
    "latitude": 47.5969162,
    "longitude": -122.3220442,
    "isPremium": False,
    "phoneNumber": "1206-880-8654",
    "emailAddress": "info@tabletopvillage.com",
    "website": "https://tabletopvillage.com/",
    "distance": 1234,
}

SAMPLE_API_STORE_PREMIUM: dict[str, object] = {
    "id": "10285",
    "name": "Mox Boarding House",
    "postalAddress": "5105 Leary Ave NW, Seattle, WA, 98107, United States",
    "latitude": 47.6651,
    "longitude": -122.3784,
    "isPremium": True,
    "phoneNumber": "2065551234",
    "emailAddress": None,
    "website": "https://moxboardinghouse.com/",
    "distance": 5000,
}

SAMPLE_API_STORE_MINIMAL: dict[str, object] = {
    "id": "99999",
    "name": "Bare Bones Games",
    "postalAddress": "100 Test Rd, Austin, TX, 78701, United States",
    "latitude": None,
    "longitude": None,
    "isPremium": False,
    "phoneNumber": None,
    "emailAddress": None,
    "website": None,
    "distance": 0,
}


class TestParsePostalAddress:
    """Tests for _parse_postal_address()."""

    def test_full_address(self) -> None:
        result = _parse_postal_address(
            "616 8th Ave S, Seattle, WA, 98104, United States"
        )
        assert result["street"] == "616 8th Ave S"
        assert result["city"] == "Seattle"
        assert result["state"] == "WA"
        assert result["zip_code"] == "98104"
        assert result["country"] == "United States"

    def test_four_parts(self) -> None:
        result = _parse_postal_address("100 Main St, Portland, OR, 97201")
        assert result["street"] == "100 Main St"
        assert result["city"] == "Portland"
        assert result["state"] == "OR"
        assert result["zip_code"] == "97201"

    def test_three_parts(self) -> None:
        result = _parse_postal_address("100 Main St, Portland, OR")
        assert result["street"] == "100 Main St"
        assert result["city"] == "Portland"
        assert result["state"] == "OR"
        assert result["zip_code"] == ""

    def test_single_part(self) -> None:
        result = _parse_postal_address("Some Address")
        assert result["street"] == "Some Address"
        assert result["city"] == ""

    def test_extra_whitespace(self) -> None:
        result = _parse_postal_address("  100 Main St ,  Portland , OR , 97201 , US  ")
        assert result["street"] == "100 Main St"
        assert result["city"] == "Portland"
        assert result["state"] == "OR"


class TestApiStoreToRaw:
    """Tests for _api_store_to_raw()."""

    def test_full_store(self) -> None:
        raw = _api_store_to_raw(SAMPLE_API_STORE)
        assert raw is not None
        assert raw.wpn_id == "18077"
        assert raw.name == "Tabletop Village"
        assert raw.street == "616 8th Ave S"
        assert raw.city == "Seattle"
        assert raw.state == "WA"
        assert raw.zip_code == "98104"
        assert raw.phone == "1206-880-8654"
        assert raw.latitude == pytest.approx(47.5969162)
        assert raw.is_premium is False
        assert raw.wpn_level_str == "core"

    def test_premium_store(self) -> None:
        raw = _api_store_to_raw(SAMPLE_API_STORE_PREMIUM)
        assert raw is not None
        assert raw.is_premium is True
        assert raw.wpn_level_str == "premium"

    def test_minimal_store(self) -> None:
        raw = _api_store_to_raw(SAMPLE_API_STORE_MINIMAL)
        assert raw is not None
        assert raw.phone is None
        assert raw.website is None
        assert raw.latitude is None

    def test_missing_postal_address(self) -> None:
        data = dict(SAMPLE_API_STORE)
        data["postalAddress"] = ""
        assert _api_store_to_raw(data) is None

    def test_missing_name(self) -> None:
        data = dict(SAMPLE_API_STORE)
        data["name"] = ""
        assert _api_store_to_raw(data) is None


class TestWpnStoreRaw:
    """Tests for the WpnStoreRaw pydantic model."""

    def test_creation(self) -> None:
        store = WpnStoreRaw(
            wpn_id="123",
            name="Test Store",
            street="100 Main St",
            city="Portland",
            state="OR",
            zip_code="97201",
            country="United States",
        )
        assert store.wpn_id == "123"
        assert store.is_premium is False

    def test_wpn_level_str(self) -> None:
        core = WpnStoreRaw(
            wpn_id="1", name="Core", street="1 A", city="B", state="OR",
            zip_code="97201", country="US", is_premium=False,
        )
        premium = WpnStoreRaw(
            wpn_id="2", name="Premium", street="2 B", city="C", state="WA",
            zip_code="98101", country="US", is_premium=True,
        )
        assert core.wpn_level_str == "core"
        assert premium.wpn_level_str == "premium"


class TestCacheRoundTrip:
    """Tests for save/load cache functions."""

    def test_round_trip(self, tmp_path: Path) -> None:
        stores = [
            WpnStoreRaw(
                wpn_id="100", name="Store A", street="1 Main", city="A",
                state="OR", zip_code="97201", country="US",
            ),
            WpnStoreRaw(
                wpn_id="200", name="Store B", street="2 Oak", city="B",
                state="WA", zip_code="98101", country="US", is_premium=True,
            ),
        ]
        cache_path = tmp_path / "test_cache.json"
        save_raw_to_cache(stores, cache_path)

        assert cache_path.exists()
        loaded = load_raw_from_cache(cache_path)
        assert len(loaded) == 2
        assert loaded[0].wpn_id == "100"
        assert loaded[1].is_premium is True

    def test_load_nonexistent_raises(self, tmp_path: Path) -> None:
        with pytest.raises(AssertionError):
            load_raw_from_cache(tmp_path / "nope.json")

    def test_cache_is_valid_json(self, tmp_path: Path) -> None:
        stores = [
            WpnStoreRaw(
                wpn_id="1", name="Test", street="1 A", city="B",
                state="OR", zip_code="97201", country="US",
            ),
        ]
        cache_path = tmp_path / "test.json"
        save_raw_to_cache(stores, cache_path)

        data = json.loads(cache_path.read_text())
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["wpn_id"] == "1"
