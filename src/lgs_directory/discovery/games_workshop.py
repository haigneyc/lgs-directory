"""Games Workshop Retailer Locator scraper — discovers hobby/miniatures shops."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

from lgs_directory.discovery.base_scraper import (
    BaseScraper,
    load_from_cache,
    save_to_cache,
)

logger = logging.getLogger(__name__)

# Games Workshop retailer locator API endpoint
_API_URL = "https://www.games-workshop.com/en-US/store/storefinder"

# Search grid over contiguous US (coarse 2-degree grid)
_US_LAT_MIN = 25
_US_LAT_MAX = 49
_US_LNG_MIN = -125
_US_LNG_MAX = -66
_GRID_STEP = 2

_SEARCH_RADIUS_MILES = 100
_MAX_PAGES = 400  # Safety cap on total API calls — covers full US grid (~360 cells)
_REQUEST_DELAY_SECS = 1.0
_MAX_STORES_PER_REQUEST = 100

_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "lgs-directory/0.1.0",
}


class GamesWorkshopStoreRaw(BaseModel):
    """Raw store record from the Games Workshop retailer locator."""

    gw_id: str
    name: str
    street: str
    city: str
    state: str
    zip_code: str
    country: str
    phone: str | None = None
    website: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    store_type: str | None = None  # e.g., "Independent Retailer", "GW Store"


def _parse_gw_store(data: dict[str, Any]) -> GamesWorkshopStoreRaw | None:
    """Parse a single GW retailer result into GamesWorkshopStoreRaw.

    Returns None if required fields are missing.
    """
    assert isinstance(data, dict), "data must be a dict"

    store_id = data.get("id", "")
    name = data.get("name", "")
    if not store_id or not name:
        logger.warning("GW store missing id or name, skipping: %s", store_id)
        return None

    address = data.get("address", {})
    if not isinstance(address, dict):
        # Gracefully skip non-dict address data (e.g., flat string)
        logger.debug("GW store %s has non-dict address, skipping", store_id)
        return None

    assert isinstance(address, dict)

    street = address.get("line1", "")
    city = address.get("town", "")
    state = address.get("region", "")
    zip_code = address.get("postalCode", "")
    country = address.get("country", "")

    if not street or not city:
        logger.warning("GW store %s has incomplete address, skipping", store_id)
        return None

    result = GamesWorkshopStoreRaw(
        gw_id=str(store_id),
        name=name,
        street=street,
        city=city,
        state=state,
        zip_code=zip_code,
        country=country,
        phone=data.get("phone"),
        website=data.get("website"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        store_type=data.get("storeType"),
    )
    assert result.gw_id == str(store_id)
    return result


class GamesWorkshopScraper(BaseScraper):
    """Scrapes the Games Workshop retailer locator for hobby/miniatures stores."""

    def __init__(
        self,
        delay: float = _REQUEST_DELAY_SECS,
    ) -> None:
        super().__init__(delay=delay, headers=_HEADERS)

    def _fetch_nearby(
        self,
        lat: float,
        lng: float,
        radius_miles: int = _SEARCH_RADIUS_MILES,
    ) -> list[dict[str, Any]]:
        """Fetch stores near a lat/lng point."""
        assert -90 <= lat <= 90, f"Invalid latitude: {lat}"
        assert -180 <= lng <= 180, f"Invalid longitude: {lng}"

        params = {
            "latitude": str(lat),
            "longitude": str(lng),
            "radius": str(radius_miles),
            "country": "US",
            "maxResults": str(_MAX_STORES_PER_REQUEST),
        }

        client = self._get_client()
        response = client.get(_API_URL, params=params)
        response.raise_for_status()

        data = response.json()
        assert isinstance(data, (dict, list)), "API response must be dict or list"

        # Response shape varies; normalize to list of stores
        stores = data.get("stores", data.get("results", [])) if isinstance(data, dict) else data

        assert isinstance(stores, list)
        return stores

    def _generate_grid_cells(self) -> list[tuple[float, float]]:
        """Generate lat/lng grid cells covering the contiguous US."""
        cells: list[tuple[float, float]] = []
        max_cells = 5000  # safety cap
        lat = _US_LAT_MIN
        while lat <= _US_LAT_MAX and len(cells) < max_cells:
            lng = _US_LNG_MIN
            while lng <= _US_LNG_MAX and len(cells) < max_cells:
                cells.append((lat + _GRID_STEP / 2, lng + _GRID_STEP / 2))
                lng += _GRID_STEP
            lat += _GRID_STEP
        assert len(cells) > 0, "Grid must produce at least one cell"
        return cells

    def fetch_stores(self, max_requests: int | None = None) -> list[GamesWorkshopStoreRaw]:
        """Fetch all GW-listed retailers across the US via grid scan.

        Returns deduplicated list of GamesWorkshopStoreRaw records.
        """
        cells = self._generate_grid_cells()
        seen_ids: set[str] = set()
        all_stores: list[GamesWorkshopStoreRaw] = []
        request_count = 0
        request_cap = max_requests or _MAX_PAGES

        assert request_cap > 0, "max_requests must be positive"

        logger.info(
            "Scanning %d grid cells for GW retailers (max %d requests)",
            len(cells), request_cap,
        )

        for cell_idx, (lat, lng) in enumerate(cells):
            if request_count >= request_cap:
                logger.info("Reached request cap (%d), stopping", request_cap)
                break

            try:
                raw_stores = self._fetch_nearby(lat, lng)
                request_count += 1
            except httpx.HTTPError as exc:
                request_count += 1
                logger.warning("HTTP error for cell (%s, %s): %s", lat, lng, exc)
                continue

            for item in raw_stores:
                parsed = _parse_gw_store(item)
                if parsed is not None and parsed.gw_id not in seen_ids:
                    seen_ids.add(parsed.gw_id)
                    all_stores.append(parsed)

            if (cell_idx + 1) % 25 == 0:
                logger.info(
                    "Scanned %d / %d cells, found %d unique stores (%d requests)",
                    cell_idx + 1, len(cells), len(all_stores), request_count,
                )

            if self._delay > 0:
                time.sleep(self._delay)

        logger.info("Total GW retailers found: %d (%d requests)", len(all_stores), request_count)
        assert isinstance(all_stores, list)
        return all_stores


def save_raw_to_cache(stores: list[GamesWorkshopStoreRaw], path: Path) -> None:
    """Save parsed GW stores to a JSON cache file."""
    save_to_cache(stores, path, label="GW stores")


def load_raw_from_cache(path: Path) -> list[GamesWorkshopStoreRaw]:
    """Load GW stores from a JSON cache file."""
    return load_from_cache(path, GamesWorkshopStoreRaw, label="GW stores")
