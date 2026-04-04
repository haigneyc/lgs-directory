"""Retro game store scraper — Video Game Sage / Racketboy directories."""

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

# Video Game Sage store directory
_VGS_URL = "https://www.videogamesage.com/stores"

# Racketboy retro gaming store directory
_RACKETBOY_URL = "https://www.racketboy.com/retro/retro-gaming-stores"

# US state codes for iterating
_US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
]

_MAX_STORES_PER_STATE = 200  # Safety cap per state
_REQUEST_DELAY_SECS = 1.5
_MAX_TOTAL_REQUESTS = 200  # Safety cap on total requests

_HEADERS = {
    "Accept": "application/json, text/html",
    "User-Agent": "lgs-directory/0.1.0",
}


class RetroGameStoreRaw(BaseModel):
    """Raw store record from a retro game store directory."""

    source_id: str
    source: str  # "video_game_sage" or "racketboy"
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


def _parse_vgs_store(data: dict[str, Any]) -> RetroGameStoreRaw | None:
    """Parse a Video Game Sage store entry.

    Returns None if required fields are missing.
    """
    assert isinstance(data, dict), "data must be a dict"

    store_id = data.get("id", data.get("slug", ""))
    name = data.get("name", data.get("title", ""))
    if not store_id or not name:
        logger.warning("VGS store missing id or name, skipping")
        return None

    street = data.get("street", data.get("address", ""))
    city = data.get("city", "")
    state = data.get("state", "")
    zip_code = data.get("zip", data.get("zip_code", data.get("postal_code", "")))

    if not street or not city:
        logger.warning("VGS store %s has incomplete address, skipping", store_id)
        return None

    result = RetroGameStoreRaw(
        source_id=str(store_id),
        source="video_game_sage",
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


def _parse_racketboy_store(data: dict[str, Any]) -> RetroGameStoreRaw | None:
    """Parse a Racketboy store entry.

    Returns None if required fields are missing.
    """
    assert isinstance(data, dict), "data must be a dict"

    store_id = data.get("id", data.get("slug", ""))
    name = data.get("name", data.get("title", ""))
    if not store_id or not name:
        logger.warning("Racketboy store missing id or name, skipping")
        return None

    street = data.get("street", data.get("address", ""))
    city = data.get("city", "")
    state = data.get("state", "")
    zip_code = data.get("zip", data.get("zip_code", data.get("postal_code", "")))

    if not street or not city:
        logger.warning("Racketboy store %s has incomplete address, skipping", store_id)
        return None

    result = RetroGameStoreRaw(
        source_id=str(store_id),
        source="racketboy",
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


class RetroGameScraper(BaseScraper):
    """Scrapes retro game store directories for shop listings."""

    def __init__(
        self,
        delay: float = _REQUEST_DELAY_SECS,
    ) -> None:
        super().__init__(delay=delay, headers=_HEADERS)

    def _fetch_state_stores(self, state: str) -> list[dict[str, Any]]:
        """Fetch retro game stores for a single US state from Video Game Sage."""
        assert isinstance(state, str) and len(state) == 2, f"Invalid state: {state}"

        client = self._get_client()
        params = {
            "state": state,
            "country": "US",
            "limit": str(_MAX_STORES_PER_STATE),
        }

        response = client.get(_VGS_URL, params=params)
        response.raise_for_status()

        data = response.json()
        assert isinstance(data, (dict, list)), "API response must be dict or list"

        stores = data.get("stores", data.get("results", [])) if isinstance(data, dict) else data

        assert isinstance(stores, list)
        return stores

    def fetch_stores(self, max_requests: int | None = None) -> list[RetroGameStoreRaw]:
        """Fetch retro game stores across all US states.

        Returns deduplicated list of RetroGameStoreRaw records.
        """
        seen_ids: set[str] = set()
        all_stores: list[RetroGameStoreRaw] = []
        request_count = 0
        request_cap = max_requests or _MAX_TOTAL_REQUESTS

        assert request_cap > 0, "max_requests must be positive"

        logger.info(
            "Scanning %d US states for retro game stores (max %d requests)",
            len(_US_STATES), request_cap,
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
                parsed = _parse_vgs_store(item)
                if parsed is not None and parsed.source_id not in seen_ids:
                    seen_ids.add(parsed.source_id)
                    all_stores.append(parsed)

            if (state_idx + 1) % 10 == 0:
                logger.info(
                    "Scanned %d / %d states, found %d unique stores (%d requests)",
                    state_idx + 1, len(_US_STATES), len(all_stores), request_count,
                )

            if self._delay > 0:
                time.sleep(self._delay)

        logger.info(
            "Total retro game stores found: %d (%d requests)",
            len(all_stores), request_count,
        )
        assert isinstance(all_stores, list)
        return all_stores


def save_raw_to_cache(stores: list[RetroGameStoreRaw], path: Path) -> None:
    """Save parsed retro game stores to a JSON cache file."""
    save_to_cache(stores, path, label="retro game stores")


def load_raw_from_cache(path: Path) -> list[RetroGameStoreRaw]:
    """Load retro game stores from a JSON cache file."""
    return load_from_cache(path, RetroGameStoreRaw, label="retro game stores")
