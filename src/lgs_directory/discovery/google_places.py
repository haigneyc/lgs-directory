"""Google Places API scraper — discovers game stores via Text Search."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

_SEARCH_CATEGORIES = [
    "game store",
    "hobby shop",
    "card game store",
    "comic book store",
    "retro video game store",
    "used video game store",
    "warhammer store",
]

# 1-degree grid over contiguous US
_US_LAT_MIN = 24
_US_LAT_MAX = 50
_US_LNG_MIN = -125
_US_LNG_MAX = -66

_RADIUS_METERS = 50_000  # 50km search radius
_MAX_PAGES_PER_CELL = 3  # 20 results per page = 60 max
_REQUEST_DELAY_SECS = 0.3


def _apply_grid_shard(
    cells: list[tuple[float, float]],
    shard_index: int | None,
    shard_count: int | None,
) -> list[tuple[float, float]]:
    """Return the subset of grid cells assigned to one shard.

    Uses modulo striding so each shard covers the full geographic extent
    rather than a contiguous block.
    """
    assert isinstance(cells, list), "cells must be a list"

    if shard_index is None and shard_count is None:
        return cells

    assert shard_index is not None, "shard_index required when shard_count is set"
    assert shard_count is not None, "shard_count required when shard_index is set"
    assert shard_count > 0, "shard_count must be positive"
    assert 0 <= shard_index < shard_count, "shard_index must be within shard_count"

    sharded_cells = [
        cell
        for idx, cell in enumerate(cells)
        if idx % shard_count == shard_index
    ]

    assert len(sharded_cells) > 0, "Shard selection produced no cells"
    return sharded_cells


class GooglePlaceRaw(BaseModel):
    """Raw place record from Google Places API."""

    place_id: str
    name: str
    address: str
    phone: str | None = None
    website: str | None = None
    lat: float | None = None
    lng: float | None = None
    rating: float | None = None
    types: list[str] = []


def _parse_place(data: dict[str, Any]) -> GooglePlaceRaw | None:
    """Parse a single Places API result into GooglePlaceRaw.

    Returns None if the place lacks required fields.
    """
    assert isinstance(data, dict), "place data must be a dict"

    place_id = data.get("id", "")
    name = data.get("displayName", {}).get("text", "")
    address = data.get("formattedAddress", "")

    if not place_id or not name or not address:
        logger.warning("Skipping place with missing fields: %s", place_id)
        return None

    location = data.get("location", {})

    result = GooglePlaceRaw(
        place_id=place_id,
        name=name,
        address=address,
        phone=data.get("nationalPhoneNumber"),
        website=data.get("websiteUri"),
        lat=location.get("latitude"),
        lng=location.get("longitude"),
        rating=data.get("rating"),
        types=data.get("types", []),
    )
    assert result.place_id == place_id
    return result


class GooglePlacesScraper:
    """Scrapes the Google Places Text Search (New) API for game stores."""

    def __init__(
        self,
        api_key: str,
        delay: float = _REQUEST_DELAY_SECS,
    ) -> None:
        assert isinstance(api_key, str) and len(api_key) > 0, "API key required"
        assert delay >= 0, "Delay must be non-negative"
        self._api_key = api_key
        self._delay = delay
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        """Return a cached httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=30.0)
        assert self._client is not None
        return self._client

    def _search_text(
        self,
        query: str,
        lat: float,
        lng: float,
        radius_meters: int,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """Execute a single Text Search request."""
        assert -90 <= lat <= 90, f"Invalid latitude: {lat}"
        assert -180 <= lng <= 180, f"Invalid longitude: {lng}"

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.nationalPhoneNumber,places.websiteUri,"
                "places.location,places.rating,places.types,"
                "nextPageToken"
            ),
        }

        body: dict[str, Any] = {
            "textQuery": query,
            "locationBias": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(radius_meters),
                },
            },
        }
        if page_token is not None:
            body["pageToken"] = page_token

        client = self._get_client()
        response = client.post(_TEXT_SEARCH_URL, json=body, headers=headers)
        response.raise_for_status()

        data = response.json()
        assert isinstance(data, dict), "API response must be a dict"
        return data

    def _generate_grid_cells(
        self,
        limit_cells: int | None = None,
        shard_index: int | None = None,
        shard_count: int | None = None,
    ) -> list[tuple[float, float]]:
        """Generate lat/lng grid cell centers covering the contiguous US.

        When shard_index and shard_count are provided, returns only the cells
        for that shard (modulo striding over the full grid).
        """
        assert shard_index is None or shard_count is not None, (
            "shard_index requires shard_count"
        )
        assert shard_count is None or shard_count > 0, "shard_count must be positive"

        cells: list[tuple[float, float]] = []
        lat = _US_LAT_MIN
        max_cells = 10_000  # safety cap
        while lat <= _US_LAT_MAX and len(cells) < max_cells:
            lng = _US_LNG_MIN
            while lng <= _US_LNG_MAX and len(cells) < max_cells:
                cells.append((lat + 0.5, lng + 0.5))
                lng += 1
            lat += 1

        assert len(cells) > 0, "Grid must produce at least one cell"

        cells = _apply_grid_shard(cells, shard_index, shard_count)

        if limit_cells is not None:
            assert limit_cells > 0, "limit_cells must be positive"
            cells = cells[:limit_cells]

        assert len(cells) > 0, "Grid must produce at least one cell after sharding"
        return cells

    def fetch_stores(
        self,
        limit_cells: int | None = None,
        max_requests: int | None = None,
        shard_index: int | None = None,
        shard_count: int | None = None,
    ) -> list[GooglePlaceRaw]:
        """Fetch game stores across the US via grid scan.

        Args:
            limit_cells: Max grid cells to scan (for testing).
            max_requests: Max total API requests to make (for cost control).
            shard_index: Zero-based shard index to scan.
            shard_count: Total number of shards.

        Returns:
            Deduplicated list of GooglePlaceRaw records.
        """
        assert shard_index is None or shard_count is not None, (
            "shard_index requires shard_count"
        )
        assert shard_count is None or shard_count > 0, "shard_count must be positive"

        cells = self._generate_grid_cells(
            limit_cells=limit_cells,
            shard_index=shard_index,
            shard_count=shard_count,
        )
        seen_ids: set[str] = set()
        all_places: list[GooglePlaceRaw] = []
        request_count = 0
        request_cap = max_requests or 1_000_000  # effectively unlimited

        assert request_cap > 0, "max_requests must be positive"

        shard_label = "full grid"
        if shard_index is not None and shard_count is not None:
            shard_label = f"shard {shard_index + 1}/{shard_count}"

        logger.info(
            "Scanning %d grid cells from %s across %d categories (max %s requests)",
            len(cells),
            shard_label,
            len(_SEARCH_CATEGORIES),
            max_requests if max_requests is not None else "unlimited",
        )

        for cell_idx, (lat, lng) in enumerate(cells):
            if request_count >= request_cap:
                logger.info("Reached request cap (%d), stopping", request_cap)
                break

            for category in _SEARCH_CATEGORIES:
                if request_count >= request_cap:
                    break

                page_token: str | None = None
                pages_fetched = 0

                while pages_fetched < _MAX_PAGES_PER_CELL:
                    if request_count >= request_cap:
                        logger.info(
                            "Reached request cap (%d), stopping",
                            request_cap,
                        )
                        break

                    try:
                        data = self._search_text(
                            query=category,
                            lat=lat,
                            lng=lng,
                            radius_meters=_RADIUS_METERS,
                            page_token=page_token,
                        )
                        request_count += 1
                    except httpx.HTTPStatusError as exc:
                        request_count += 1
                        logger.warning(
                            "API error for cell (%s, %s) %s: %s",
                            lat,
                            lng,
                            category,
                            exc,
                        )
                        break

                    places = data.get("places", [])
                    assert isinstance(places, list)

                    for place_data in places:
                        parsed = _parse_place(place_data)
                        if parsed is not None and parsed.place_id not in seen_ids:
                            seen_ids.add(parsed.place_id)
                            all_places.append(parsed)

                    page_token = data.get("nextPageToken")
                    pages_fetched += 1

                    if page_token is None or len(places) == 0:
                        break

                    if self._delay > 0:
                        time.sleep(self._delay)

            if (cell_idx + 1) % 50 == 0:
                logger.info(
                    "Scanned %d / %d cells, found %d unique places (%d requests)",
                    cell_idx + 1,
                    len(cells),
                    len(all_places),
                    request_count,
                )

        logger.info(
            "Total unique places found: %d (%d API requests)",
            len(all_places),
            request_count,
        )
        assert isinstance(all_places, list)
        return all_places

    def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            self._client.close()


def save_raw_to_cache(stores: list[GooglePlaceRaw], path: Path) -> None:
    """Save parsed Google Places stores to a JSON cache file."""
    assert isinstance(path, Path), "path must be a Path"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [s.model_dump() for s in stores]
    path.write_text(json.dumps(data, indent=2))
    assert path.exists()
    logger.info("Saved %d Google Places stores to %s", len(data), path)


def load_raw_from_cache(path: Path) -> list[GooglePlaceRaw]:
    """Load Google Places stores from a JSON cache file."""
    assert isinstance(path, Path), "path must be a Path"
    assert path.exists(), f"Cache file not found: {path}"
    data = json.loads(path.read_text())
    assert isinstance(data, list), "Cache data must be a list"
    stores = [GooglePlaceRaw.model_validate(item) for item in data]
    logger.info("Loaded %d Google Places stores from %s", len(stores), path)
    return stores
