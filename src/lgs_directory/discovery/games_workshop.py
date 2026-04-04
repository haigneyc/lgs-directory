"""Games Workshop store finder scraper — discovers hobby/miniatures shops.

The store finder API moved from games-workshop.com to warhammer.com in early 2026.
The new endpoint returns ALL stores worldwide in a single JSON array (no pagination,
no lat/lng query params).  We filter to US stores client-side.
"""

from __future__ import annotations

import logging
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

# Warhammer store finder API — returns all stores worldwide in a single response
_API_URL = "https://www.warhammer.com/api/storefinder"

_REQUEST_DELAY_SECS = 0.0  # Single request, no rate-limiting needed

# Browser-like headers required to avoid AWS WAF captcha challenge
_HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.warhammer.com/en-US/store-finder",
}

_MAX_RESPONSE_STORES = 20_000  # Safety cap on total stores in a single response


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
    """Parse a single store from the warhammer.com store finder API.

    The new API uses flat fields (addressLine1, region, postalCode, countryCode)
    and nests coordinates under ``_geoloc``.  ``objectID`` is the stable unique key.

    Returns None if required fields are missing.
    """
    assert isinstance(data, dict), "data must be a dict"

    object_id = data.get("objectID", "")
    name = data.get("displayName") or data.get("name", "")
    if not object_id or not name:
        logger.warning("GW store missing objectID or name, skipping: %s", object_id)
        return None

    street = data.get("addressLine1", "")
    city = data.get("city", "")
    if not street or not city:
        logger.warning("GW store %s has incomplete address, skipping", object_id)
        return None

    geoloc = data.get("_geoloc", {})
    assert isinstance(geoloc, dict) or geoloc is None

    lat: float | None = geoloc.get("lat") if isinstance(geoloc, dict) else None
    lng: float | None = geoloc.get("lng") if isinstance(geoloc, dict) else None

    is_wh_store = data.get("isWarHammerStore", False)
    store_type = "GW Store" if is_wh_store else "Independent Retailer"

    result = GamesWorkshopStoreRaw(
        gw_id=str(object_id),
        name=name,
        street=street,
        city=city,
        state=data.get("region", ""),
        zip_code=data.get("postalCode", ""),
        country=data.get("countryCode", ""),
        phone=data.get("phone"),
        website=data.get("websiteUrl"),
        latitude=lat,
        longitude=lng,
        store_type=store_type,
    )
    assert result.gw_id == str(object_id)
    return result


class GamesWorkshopScraper(BaseScraper):
    """Scrapes the Warhammer store finder for hobby/miniatures stores.

    The API returns all stores worldwide in a single JSON array.
    We filter to US stores and deduplicate by objectID.
    """

    def __init__(
        self,
        delay: float = _REQUEST_DELAY_SECS,
        timeout: float = 60.0,
    ) -> None:
        assert timeout > 0, "timeout must be positive"
        super().__init__(delay=delay, headers=_HEADERS, timeout=timeout)

    def _fetch_all_stores(self) -> list[dict[str, Any]]:
        """Fetch the complete store list from the warhammer.com API."""
        client = self._get_client()
        response = client.get(_API_URL)
        response.raise_for_status()

        data = response.json()
        assert isinstance(data, list), "API response must be a JSON array"
        assert len(data) <= _MAX_RESPONSE_STORES, (
            f"Response contains {len(data)} stores, exceeds safety cap"
        )
        return data

    def fetch_stores(self, max_requests: int | None = None) -> list[GamesWorkshopStoreRaw]:
        """Fetch all GW-listed US retailers from the store finder API.

        The ``max_requests`` parameter is accepted for CLI compatibility but
        has no practical effect — the new API returns everything in one call.

        Returns deduplicated list of GamesWorkshopStoreRaw records.
        """
        # max_requests kept for interface compat; cap is always 1
        _ = max_requests

        logger.info("Fetching all stores from %s", _API_URL)

        try:
            raw_items = self._fetch_all_stores()
        except httpx.HTTPError as exc:
            logger.error("HTTP error fetching store finder: %s", exc)
            return []

        assert isinstance(raw_items, list)
        logger.info("API returned %d stores worldwide", len(raw_items))

        seen_ids: set[str] = set()
        us_stores: list[GamesWorkshopStoreRaw] = []

        for item in raw_items:
            # Filter to US stores only
            country_code = item.get("countryCode", "")
            if country_code != "US":
                continue

            parsed = _parse_gw_store(item)
            if parsed is not None and parsed.gw_id not in seen_ids:
                seen_ids.add(parsed.gw_id)
                us_stores.append(parsed)

        assert isinstance(us_stores, list)
        logger.info("Total US GW retailers found: %d", len(us_stores))
        return us_stores


def save_raw_to_cache(stores: list[GamesWorkshopStoreRaw], path: Path) -> None:
    """Save parsed GW stores to a JSON cache file."""
    save_to_cache(stores, path, label="GW stores")


def load_raw_from_cache(path: Path) -> list[GamesWorkshopStoreRaw]:
    """Load GW stores from a JSON cache file."""
    return load_from_cache(path, GamesWorkshopStoreRaw, label="GW stores")
