"""WPN Store Locator scraper — fetches stores via the WotC GraphQL API."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# GraphQL endpoint for the WPN store locator
_API_URL = "https://api.tabletop.wizards.com/silverbeak-griffin-service/graphql"

_STORE_QUERY = """
query getStoresByLocation(
    $latitude: Float!, $longitude: Float!, $maxMeters: Int!,
    $pageSize: Int, $page: Int, $isPremium: Boolean
) {
    storesByLocation(input: {
        latitude: $latitude, longitude: $longitude, maxMeters: $maxMeters,
        pageSize: $pageSize, page: $page, isPremium: $isPremium
    }) {
        stores {
            id name postalAddress latitude longitude isPremium
            phoneNumber emailAddress website distance
        }
        pageInfo { page pageSize totalResults }
    }
}
""".strip()

# Center of the contiguous US (geographic center of Kansas)
_US_CENTER_LAT = 39.8283
_US_CENTER_LNG = -98.5795

# 5000 km — covers all of contiguous US plus Alaska/Hawaii overlap
_US_RADIUS_METERS = 5_000_000

_PAGE_SIZE = 1000
_MAX_PAGES = 50  # Safety cap: 50 * 1000 = 50k stores max
_REQUEST_DELAY_SECS = 1.0

# Default client headers
_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "lgs-directory/0.1.0",
}


class WpnStoreRaw(BaseModel):
    """Raw store record from the WPN API, before normalization."""

    wpn_id: str
    name: str
    street: str
    city: str
    state: str
    zip_code: str
    country: str
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_premium: bool = False

    @property
    def wpn_level_str(self) -> str:
        """Return WPN level as a string matching our enum values."""
        return "premium" if self.is_premium else "core"


def _parse_postal_address(raw: str) -> dict[str, str]:
    """Parse the WPN postalAddress string into components.

    Format: "616 8th Ave S, Seattle, WA, 98104, United States"
    Some addresses may be malformed — we handle missing parts gracefully.
    """
    assert isinstance(raw, str), "postalAddress must be a string"
    parts = [p.strip() for p in raw.split(",")]

    result: dict[str, str] = {
        "street": "",
        "city": "",
        "state": "",
        "zip_code": "",
        "country": "",
    }

    # Expected: street, city, state, zip, country (5 parts)
    # But some addresses may have fewer parts
    if len(parts) >= 5:
        result["street"] = parts[0]
        result["city"] = parts[1]
        result["state"] = parts[2]
        result["zip_code"] = parts[3]
        result["country"] = parts[4]
    elif len(parts) == 4:
        result["street"] = parts[0]
        result["city"] = parts[1]
        result["state"] = parts[2]
        result["zip_code"] = parts[3]
    elif len(parts) == 3:
        result["street"] = parts[0]
        result["city"] = parts[1]
        result["state"] = parts[2]
    elif len(parts) >= 1:
        result["street"] = parts[0]

    assert "street" in result
    return result


def _api_store_to_raw(store_data: dict[str, Any]) -> WpnStoreRaw | None:
    """Convert a single API store response dict to WpnStoreRaw.

    Returns None if the store cannot be parsed (missing required fields).
    """
    assert isinstance(store_data, dict), "store_data must be a dict"

    postal = store_data.get("postalAddress", "")
    if not postal:
        logger.warning("Store %s has no postalAddress, skipping", store_data.get("id"))
        return None

    addr = _parse_postal_address(postal)
    assert isinstance(addr, dict)

    # Skip stores with no street (unusable for dedup)
    if not addr["street"]:
        logger.warning("Store %s has empty street, skipping", store_data.get("id"))
        return None

    store_id = store_data.get("id", "")
    name = store_data.get("name", "")
    if not name:
        logger.warning("Store %s has no name, skipping", store_id)
        return None

    return WpnStoreRaw(
        wpn_id=str(store_id),
        name=name,
        street=addr["street"],
        city=addr["city"],
        state=addr["state"],
        zip_code=addr["zip_code"],
        country=addr["country"],
        phone=store_data.get("phoneNumber"),
        email=store_data.get("emailAddress"),
        website=store_data.get("website"),
        latitude=store_data.get("latitude"),
        longitude=store_data.get("longitude"),
        is_premium=store_data.get("isPremium", False),
    )


class WpnScraper:
    """Scrapes the WPN Store Locator GraphQL API."""

    def __init__(
        self,
        delay: float = _REQUEST_DELAY_SECS,
        cookies: dict[str, str] | None = None,
    ) -> None:
        assert delay >= 0, "Delay must be non-negative"
        self._delay = delay
        self._cookies = cookies
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        """Return a cached httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                headers=_HEADERS,
                timeout=30.0,
                cookies=self._cookies,
            )
        assert self._client is not None
        return self._client

    def _fetch_page(
        self,
        lat: float,
        lng: float,
        radius_meters: int,
        page: int,
    ) -> dict[str, Any]:
        """Fetch a single page of store results from the API."""
        assert -90 <= lat <= 90, f"Invalid latitude: {lat}"
        assert -180 <= lng <= 180, f"Invalid longitude: {lng}"

        payload = {
            "operationName": "getStoresByLocation",
            "variables": {
                "latitude": lat,
                "longitude": lng,
                "maxMeters": radius_meters,
                "pageSize": _PAGE_SIZE,
                "page": page,
                "isPremium": False,
            },
            "query": _STORE_QUERY,
        }

        client = self._get_client()
        response = client.post(_API_URL, json=payload)
        response.raise_for_status()

        data = response.json()
        assert isinstance(data, dict), "API response must be a dict"
        return data

    def fetch_stores_raw(
        self,
        lat: float = _US_CENTER_LAT,
        lng: float = _US_CENTER_LNG,
        radius_meters: int = _US_RADIUS_METERS,
    ) -> list[dict[str, Any]]:
        """Fetch all store records from the API via pagination.

        Returns raw API response dicts (not yet parsed to WpnStoreRaw).
        """
        all_stores: list[dict[str, Any]] = []
        page = 0

        while page < _MAX_PAGES:
            logger.info("Fetching WPN stores page %d ...", page)
            data = self._fetch_page(lat, lng, radius_meters, page)

            stores_data = data.get("data", {}).get("storesByLocation", {})
            stores = stores_data.get("stores", [])
            page_info = stores_data.get("pageInfo", {})

            assert isinstance(stores, list), "stores must be a list"
            all_stores.extend(stores)

            total = page_info.get("totalResults", 0)
            fetched = (page + 1) * _PAGE_SIZE
            logger.info(
                "  Page %d: got %d stores (total available: %d)",
                page, len(stores), total,
            )

            if fetched >= total or len(stores) == 0:
                break

            page += 1
            if self._delay > 0:
                time.sleep(self._delay)

        assert isinstance(all_stores, list)
        logger.info("Fetched %d total raw store records", len(all_stores))
        return all_stores

    def fetch_stores(
        self,
        lat: float = _US_CENTER_LAT,
        lng: float = _US_CENTER_LNG,
        radius_meters: int = _US_RADIUS_METERS,
    ) -> list[WpnStoreRaw]:
        """Fetch and parse all WPN stores.

        Returns parsed WpnStoreRaw models, skipping unparseable records.
        """
        raw_data = self.fetch_stores_raw(lat, lng, radius_meters)
        stores: list[WpnStoreRaw] = []
        skipped = 0

        for item in raw_data:
            parsed = _api_store_to_raw(item)
            if parsed is not None:
                stores.append(parsed)
            else:
                skipped += 1

        logger.info("Parsed %d stores, skipped %d", len(stores), skipped)
        assert len(stores) + skipped == len(raw_data)
        return stores

    def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            self._client.close()


def save_raw_to_cache(stores: list[WpnStoreRaw], path: Path) -> None:
    """Save parsed WPN stores to a JSON cache file."""
    assert isinstance(path, Path), "path must be a Path"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [s.model_dump() for s in stores]
    path.write_text(json.dumps(data, indent=2))
    assert path.exists()
    logger.info("Saved %d stores to %s", len(data), path)


def load_raw_from_cache(path: Path) -> list[WpnStoreRaw]:
    """Load WPN stores from a JSON cache file."""
    assert isinstance(path, Path), "path must be a Path"
    assert path.exists(), f"Cache file not found: {path}"
    data = json.loads(path.read_text())
    assert isinstance(data, list), "Cache data must be a list"
    stores = [WpnStoreRaw.model_validate(item) for item in data]
    logger.info("Loaded %d stores from %s", len(stores), path)
    return stores
