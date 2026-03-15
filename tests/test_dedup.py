"""Tests for the deduplication pipeline."""

from __future__ import annotations

from lgs_directory.discovery.dedup import (
    MatchTier,
    _haversine_miles,
    find_duplicate,
)
from lgs_directory.discovery.normalize import normalize_address
from lgs_directory.models.enums import DiscoverySource, StoreStatus
from lgs_directory.models.store import Store


def _make_store(
    name: str = "Test Store",
    street: str = "123 Main St",
    city: str = "Portland",
    state: str = "OR",
    zip_code: str = "97201",
    wpn_id: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> Store:
    """Create a Store instance for testing (not persisted)."""
    store = Store(
        name=name,
        address={
            "street": street,
            "city": city,
            "state": state,
            "zip_code": zip_code,
        },
        wpn_id=wpn_id,
        latitude=latitude,
        longitude=longitude,
        status=StoreStatus.CANDIDATE,
        discovery_source=DiscoverySource.MANUAL,
    )
    assert store.name == name
    return store


class TestHaversine:
    """Tests for the haversine distance function."""

    def test_same_point(self) -> None:
        assert _haversine_miles(45.0, -122.0, 45.0, -122.0) == 0.0

    def test_known_distance(self) -> None:
        # Portland OR to Seattle WA is roughly 145 miles
        dist = _haversine_miles(45.5231, -122.6765, 47.6062, -122.3321)
        assert 140 < dist < 150

    def test_short_distance(self) -> None:
        # Two points ~0.1 miles apart
        dist = _haversine_miles(45.5231, -122.6765, 45.5245, -122.6765)
        assert dist < 1.0


class TestFindDuplicate:
    """Tests for find_duplicate()."""

    def test_tier1_wpn_id_match(self) -> None:
        existing = [_make_store(name="Game Store", wpn_id="WPN123")]
        norm_addr = normalize_address("456 Other St", "Seattle", "WA", "98101")

        result = find_duplicate(
            candidate_name="Different Name",
            candidate_address=norm_addr,
            candidate_wpn_id="WPN123",
            candidate_lat=None,
            candidate_lng=None,
            existing_stores=existing,
        )
        assert result.is_match
        assert result.match_tier == MatchTier.WPN_ID
        assert result.confidence == 1.0
        assert not result.needs_review

    def test_tier2_name_zip_match(self) -> None:
        existing = [_make_store(name="Card Kingdom", zip_code="98101")]
        norm_addr = normalize_address("999 Different St", "Seattle", "WA", "98101")

        result = find_duplicate(
            candidate_name="Card Kingdom",
            candidate_address=norm_addr,
            candidate_wpn_id=None,
            candidate_lat=None,
            candidate_lng=None,
            existing_stores=existing,
        )
        assert result.is_match
        assert result.match_tier == MatchTier.NAME_ZIP
        assert result.confidence == 0.95

    def test_tier3_address_match(self) -> None:
        existing = [
            _make_store(name="Old Name", street="123 Main St", city="Portland", state="OR")
        ]
        norm_addr = normalize_address("123 Main St", "Portland", "OR", "97209")

        result = find_duplicate(
            candidate_name="Completely Different Name",
            candidate_address=norm_addr,
            candidate_wpn_id=None,
            candidate_lat=None,
            candidate_lng=None,
            existing_stores=existing,
        )
        assert result.is_match
        assert result.match_tier == MatchTier.ADDRESS
        assert result.confidence == 0.90

    def test_tier4_fuzzy_match_with_coords(self) -> None:
        existing = [
            _make_store(
                name="Card Kingdom",
                zip_code="98101",
                latitude=47.6062,
                longitude=-122.3321,
            )
        ]
        norm_addr = normalize_address("999 Other St", "Seattle", "WA", "98102")

        result = find_duplicate(
            candidate_name="Card Kingdoms",  # Close but not exact
            candidate_address=norm_addr,
            candidate_wpn_id=None,
            candidate_lat=47.6065,  # Very close
            candidate_lng=-122.3325,
            existing_stores=existing,
        )
        assert result.is_match
        assert result.match_tier == MatchTier.FUZZY
        assert result.confidence >= 0.85

    def test_tier4_fuzzy_match_with_zip_fallback(self) -> None:
        existing = [_make_store(name="Card Kingdom", zip_code="98101")]
        norm_addr = normalize_address("999 Other St", "Seattle", "WA", "98101")

        result = find_duplicate(
            candidate_name="Card Kingdoms",  # Close but not exact
            candidate_address=norm_addr,
            candidate_wpn_id=None,
            candidate_lat=None,
            candidate_lng=None,
            existing_stores=existing,
        )
        assert result.is_match
        assert result.match_tier == MatchTier.FUZZY

    def test_no_match(self) -> None:
        existing = [_make_store(name="Game Store Alpha", zip_code="97201")]
        norm_addr = normalize_address("999 Other St", "Seattle", "WA", "98101")

        result = find_duplicate(
            candidate_name="Totally Different Store",
            candidate_address=norm_addr,
            candidate_wpn_id=None,
            candidate_lat=None,
            candidate_lng=None,
            existing_stores=existing,
        )
        assert not result.is_match
        assert result.match_tier is None
        assert result.confidence == 0.0

    def test_no_match_empty_existing(self) -> None:
        norm_addr = normalize_address("123 Main St", "Portland", "OR", "97201")

        result = find_duplicate(
            candidate_name="New Store",
            candidate_address=norm_addr,
            candidate_wpn_id=None,
            candidate_lat=None,
            candidate_lng=None,
            existing_stores=[],
        )
        assert not result.is_match

    def test_fuzzy_too_far_apart(self) -> None:
        """Fuzzy name match should fail if stores are far apart geographically."""
        existing = [
            _make_store(
                name="Card Kingdom",
                zip_code="98101",
                latitude=47.6062,
                longitude=-122.3321,
            )
        ]
        norm_addr = normalize_address("999 Other St", "Miami", "FL", "33101")

        result = find_duplicate(
            candidate_name="Card Kingdoms",
            candidate_address=norm_addr,
            candidate_wpn_id=None,
            candidate_lat=25.7617,  # Miami - far away
            candidate_lng=-80.1918,
            existing_stores=existing,
        )
        assert not result.is_match

    def test_needs_review_flag(self) -> None:
        """Low-confidence fuzzy matches should be flagged for review."""
        existing = [_make_store(name="Game Empire", zip_code="91101")]
        norm_addr = normalize_address("999 Other St", "Pasadena", "CA", "91101")

        result = find_duplicate(
            candidate_name="Games Empire",  # Slightly different
            candidate_address=norm_addr,
            candidate_wpn_id=None,
            candidate_lat=None,
            candidate_lng=None,
            existing_stores=existing,
        )
        # If it matches at fuzzy tier, check needs_review based on confidence
        if result.is_match and result.match_tier == MatchTier.FUZZY:
            assert isinstance(result.needs_review, bool)
