"""Tests for Google Places discovery, address parsing, and ingestion."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from lgs_directory.discovery.dedup import find_duplicate
from lgs_directory.discovery.google_places import (
    GooglePlacesScraper,
    _parse_place,
)
from lgs_directory.discovery.ingest_google import _parse_google_address
from lgs_directory.models.store import Store


class TestParseGoogleAddress:
    """Tests for Google formatted address parsing."""

    def test_standard_us_address(self) -> None:
        """Parses standard US address format."""
        addr = _parse_google_address("123 Main St, Portland, OR 97201, USA")
        assert addr is not None
        assert addr.street == "123 Main St"
        assert addr.city == "Portland"
        assert addr.state == "OR"
        assert addr.zip_code == "97201"

    def test_address_without_country(self) -> None:
        """Parses address without trailing country."""
        addr = _parse_google_address("456 Oak Ave, Seattle, WA 98101")
        assert addr is not None
        assert addr.city == "Seattle"
        assert addr.state == "WA"

    def test_address_with_zip_plus_4(self) -> None:
        """Handles ZIP+4 format."""
        addr = _parse_google_address("789 Pine Rd, Denver, CO 80202-1234, USA")
        assert addr is not None
        assert addr.zip_code == "80202"
        assert addr.state == "CO"

    def test_unparseable_address(self) -> None:
        """Returns None for non-US address formats."""
        result = _parse_google_address("Some weird address without zip")
        assert result is None

    def test_empty_address(self) -> None:
        """Returns None for empty string."""
        result = _parse_google_address("")
        assert result is None


class TestParsePlace:
    """Tests for Google Places API response parsing."""

    def test_full_place(self) -> None:
        """Parses a complete place response."""
        data = {
            "id": "ChIJ123",
            "displayName": {"text": "Cool Games"},
            "formattedAddress": "123 Main St, Portland, OR 97201",
            "nationalPhoneNumber": "503-555-0100",
            "websiteUri": "https://coolgames.com",
            "location": {"latitude": 45.5, "longitude": -122.6},
            "rating": 4.5,
            "types": ["store", "point_of_interest"],
        }
        place = _parse_place(data)
        assert place is not None
        assert place.place_id == "ChIJ123"
        assert place.name == "Cool Games"
        assert place.website == "https://coolgames.com"
        assert place.lat == 45.5

    def test_minimal_place(self) -> None:
        """Parses place with only required fields."""
        data = {
            "id": "ChIJ456",
            "displayName": {"text": "Basic Store"},
            "formattedAddress": "456 Oak Ave, Seattle, WA 98101",
        }
        place = _parse_place(data)
        assert place is not None
        assert place.phone is None
        assert place.website is None

    def test_missing_name_skipped(self) -> None:
        """Place without name is skipped."""
        data = {
            "id": "ChIJ789",
            "displayName": {"text": ""},
            "formattedAddress": "789 Pine St",
        }
        result = _parse_place(data)
        assert result is None


class TestGooglePlacesScraper:
    """Tests for the Google Places scraper with mocked HTTP."""

    def test_scraper_with_mocked_response(self) -> None:
        """Scraper parses mocked API response correctly."""
        mock_response = {
            "places": [
                {
                    "id": "ChIJ_abc",
                    "displayName": {"text": "Game Haven"},
                    "formattedAddress": "100 1st Ave, Portland, OR 97201",
                    "location": {"latitude": 45.5, "longitude": -122.6},
                },
                {
                    "id": "ChIJ_def",
                    "displayName": {"text": "Card Kingdom"},
                    "formattedAddress": "200 2nd Ave, Seattle, WA 98101",
                    "location": {"latitude": 47.6, "longitude": -122.3},
                },
            ],
        }

        scraper = GooglePlacesScraper(api_key="test-key")

        mock_httpx_response = MagicMock()
        mock_httpx_response.json.return_value = mock_response
        mock_httpx_response.raise_for_status = MagicMock()

        with patch.object(scraper, "_get_client") as mock_client:
            mock_client.return_value.post.return_value = mock_httpx_response
            stores = scraper.fetch_stores(limit_cells=1)

        assert len(stores) >= 2
        ids = {s.place_id for s in stores}
        assert "ChIJ_abc" in ids
        assert "ChIJ_def" in ids

    def test_deduplicates_by_place_id(self) -> None:
        """Same place_id from different cells is not duplicated."""
        mock_response = {
            "places": [
                {
                    "id": "ChIJ_same",
                    "displayName": {"text": "Duped Store"},
                    "formattedAddress": "100 Main St, Portland, OR 97201",
                },
            ],
        }

        scraper = GooglePlacesScraper(api_key="test-key")

        mock_httpx_response = MagicMock()
        mock_httpx_response.json.return_value = mock_response
        mock_httpx_response.raise_for_status = MagicMock()

        with patch.object(scraper, "_get_client") as mock_client:
            mock_client.return_value.post.return_value = mock_httpx_response
            # 2 cells, but same place_id should only appear once
            stores = scraper.fetch_stores(limit_cells=2)

        place_ids = [s.place_id for s in stores if s.place_id == "ChIJ_same"]
        assert len(place_ids) == 1

    def test_max_requests_caps_api_calls(self) -> None:
        """max_requests stops fetching after reaching the cap."""
        call_count = 0

        def _fake_post(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.json.return_value = {
                "places": [
                    {
                        "id": f"ChIJ_{call_count}",
                        "displayName": {"text": f"Store {call_count}"},
                        "formattedAddress": f"{call_count} Main St, Portland, OR 97201",
                    },
                ],
            }
            resp.raise_for_status = MagicMock()
            return resp

        scraper = GooglePlacesScraper(api_key="test-key", delay=0)

        with patch.object(scraper, "_get_client") as mock_client:
            mock_client.return_value.post.side_effect = _fake_post
            # 2 cells × 4 categories = 8 requests, but cap at 3
            stores = scraper.fetch_stores(limit_cells=2, max_requests=3)

        assert call_count == 3
        assert len(stores) == 3


class TestDedupGooglePlaceId:
    """Tests for dedup matching on google_place_id."""

    def test_exact_google_place_id_match(self) -> None:
        """Exact google_place_id match returns confidence 1.0."""
        existing = MagicMock(spec=Store)
        existing.google_place_id = "ChIJ_match"
        existing.wpn_id = None
        existing.name = "Existing Store"
        existing.address = {
            "street": "999 Far Away Blvd",
            "city": "Faraway",
            "state": "CA",
            "zip_code": "90001",
        }

        result = find_duplicate(
            candidate_name="Different Name",
            candidate_address={
                "street": "123 OTHER", "city": "OTHER",
                "state": "OR", "zip_code": "97201",
            },
            candidate_wpn_id=None,
            candidate_lat=None,
            candidate_lng=None,
            existing_stores=[existing],
            candidate_google_place_id="ChIJ_match",
        )

        assert result.is_match
        assert result.confidence == 1.0
        assert result.matched_store == existing

    def test_no_google_place_id_no_match(self) -> None:
        """No match when google_place_ids differ."""
        existing = MagicMock(spec=Store)
        existing.google_place_id = "ChIJ_other"
        existing.wpn_id = None
        existing.name = "Unrelated Store"
        existing.address = {
            "street": "999 FAR BLVD",
            "city": "FARVILLE",
            "state": "TX",
            "zip_code": "75001",
        }
        existing.latitude = 32.0
        existing.longitude = -96.0

        result = find_duplicate(
            candidate_name="Different Store",
            candidate_address={
                "street": "123 MAIN STREET", "city": "PORTLAND",
                "state": "OR", "zip_code": "97201",
            },
            candidate_wpn_id=None,
            candidate_lat=45.5,
            candidate_lng=-122.6,
            existing_stores=[existing],
            candidate_google_place_id="ChIJ_nomatch",
        )

        assert not result.is_match
        assert result.confidence == 0.0
