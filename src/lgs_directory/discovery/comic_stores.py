"""Comic store discovery scraper — League of Comic Geeks / comicbookstores.co."""

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

# comicbookstores.co directory endpoint (JSON API)
_API_URL = "https://comicbookstores.co/api/stores"

# US state codes for iterating the directory
_US_STATES = [
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    "DC",
]

_MAX_STORES_PER_STATE = 500  # Safety cap per state
_REQUEST_DELAY_SECS = 1.0
_MAX_TOTAL_REQUESTS = 200  # Safety cap on total API calls

_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "lgs-directory/0.1.0",
}


class ComicStoreRaw(BaseModel):
    """Raw store record from a comic store directory."""

    source_id: str
    source: str  # "league_comic_geeks" or "comicbookstores"
    name: str
    street: str
    city: str
    state: str
    zip_code: str
    country: str = "US"
    phone: str | None = None
    website: str | None = None
    latitude: float | None = None
    longitude: float | None = None


def _parse_cbs_store(data: dict[str, Any]) -> ComicStoreRaw | None:
    """Parse a comicbookstores.co store entry.

    Returns None if required fields are missing.
    """
    assert isinstance(data, dict), "data must be a dict"

    store_id = data.get("id", data.get("slug", ""))
    name = data.get("name", "")
    if not store_id or not name:
        logger.warning("CBS store missing id or name, skipping")
        return None

    street = data.get("street", data.get("address", ""))
    city = data.get("city", "")
    state = data.get("state", "")
    zip_code = data.get("zip", data.get("zip_code", ""))

    if not street or not city:
        logger.warning("CBS store %s has incomplete address, skipping", store_id)
        return None

    result = ComicStoreRaw(
        source_id=str(store_id),
        source="comicbookstores",
        name=name,
        street=street,
        city=city,
        state=state,
        zip_code=zip_code,
        phone=data.get("phone"),
        website=data.get("website", data.get("url")),
        latitude=data.get("lat", data.get("latitude")),
        longitude=data.get("lng", data.get("longitude")),
    )
    assert result.source_id == str(store_id)
    return result


def _parse_lcg_store(data: dict[str, Any]) -> ComicStoreRaw | None:
    """Parse a League of Comic Geeks store entry.

    Returns None if required fields are missing.
    """
    assert isinstance(data, dict), "data must be a dict"

    store_id = str(data.get("id", ""))
    name = data.get("name", "")
    if not store_id or not name:
        logger.warning("LCG store missing id or name, skipping")
        return None

    address = data.get("address")
    if not isinstance(address, dict):
        logger.warning("LCG store %s has non-dict address, skipping", store_id)
        return None

    street = address.get("street", "")
    city = address.get("city", "")
    state = address.get("state", "")
    zip_code = address.get("zip", "")

    if not street or not city:
        logger.warning("LCG store %s has incomplete address, skipping", store_id)
        return None

    result = ComicStoreRaw(
        source_id=store_id,
        source="league_comic_geeks",
        name=name,
        street=street,
        city=city,
        state=state,
        zip_code=zip_code,
        phone=data.get("phone"),
        website=data.get("website"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
    )
    assert result.source_id == store_id
    return result


class ComicStoreScraper(BaseScraper):
    """Scrapes comic store directories for shop listings."""

    def __init__(
        self,
        delay: float = _REQUEST_DELAY_SECS,
    ) -> None:
        super().__init__(delay=delay, headers=_HEADERS)

    def _fetch_state_stores(self, state: str) -> list[dict[str, Any]]:
        """Fetch comic stores for a single US state."""
        assert isinstance(state, str) and len(state) == 2, f"Invalid state: {state}"

        client = self._get_client()
        params = {
            "state": state,
            "country": "US",
            "limit": str(_MAX_STORES_PER_STATE),
        }

        response = client.get(_API_URL, params=params)
        response.raise_for_status()

        data = response.json()
        assert isinstance(data, (dict, list)), "API response must be dict or list"

        stores = data.get("stores", data.get("results", [])) if isinstance(data, dict) else data

        assert isinstance(stores, list)
        return stores

    def fetch_stores(self, max_requests: int | None = None) -> list[ComicStoreRaw]:
        """Fetch comic stores across all US states.

        Returns deduplicated list of ComicStoreRaw records.
        """
        seen_ids: set[str] = set()
        all_stores: list[ComicStoreRaw] = []
        request_count = 0
        request_cap = max_requests or _MAX_TOTAL_REQUESTS

        assert request_cap > 0, "max_requests must be positive"

        logger.info(
            "Scanning %d US states for comic stores (max %d requests)",
            len(_US_STATES),
            request_cap,
        )

        for state_idx, state in enumerate(_US_STATES):
            if request_count >= request_cap:
                logger.info("Reached request cap (%d), stopping", request_cap)
                break

            try:
                raw_stores = self._fetch_state_stores(state)
                request_count += 1
            except httpx.HTTPError as exc:
                request_count += 1
                logger.warning("HTTP error for state %s: %s", state, exc)
                continue

            for item in raw_stores:
                parsed = _parse_cbs_store(item)
                if parsed is not None and parsed.source_id not in seen_ids:
                    seen_ids.add(parsed.source_id)
                    all_stores.append(parsed)

            if (state_idx + 1) % 10 == 0:
                logger.info(
                    "Scanned %d / %d states, found %d unique stores (%d requests)",
                    state_idx + 1,
                    len(_US_STATES),
                    len(all_stores),
                    request_count,
                )

            if self._delay > 0:
                time.sleep(self._delay)

        logger.info("Total comic stores found: %d (%d requests)", len(all_stores), request_count)
        assert isinstance(all_stores, list)
        return all_stores


def save_raw_to_cache(stores: list[ComicStoreRaw], path: Path) -> None:
    """Save parsed comic stores to a JSON cache file."""
    save_to_cache(stores, path, label="comic stores")


def load_raw_from_cache(path: Path) -> list[ComicStoreRaw]:
    """Load comic stores from a JSON cache file."""
    return load_from_cache(path, ComicStoreRaw, label="comic stores")
