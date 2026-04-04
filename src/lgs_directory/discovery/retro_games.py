"""Retro game store discovery via Google Places Text Search.

The original plan assumed Video Game Sage and Racketboy had public JSON APIs
for store directories.  Neither site exposes one (Video Game Sage is a forum,
Racketboy is a blog), so this module delegates to the Google Places (New)
Text Search API with retro-gaming-specific search terms.  Results are
converted into RetroGameStoreRaw records for the existing ingest pipeline.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from lgs_directory.discovery.base_scraper import (
    load_from_cache,
    save_to_cache,
)
from lgs_directory.discovery.google_places import GooglePlaceRaw, GooglePlacesScraper

logger = logging.getLogger(__name__)

# Retro-gaming-specific search queries for Google Places Text Search
_RETRO_SEARCH_QUERIES = [
    "retro video game store",
    "used video game store",
    "retro gaming shop",
]

# Safety caps
_MAX_TOTAL_REQUESTS = 200
_REQUEST_DELAY_SECS = 0.3

# Regex to extract state code from a US formatted address
_STATE_RE = re.compile(r",\s*([A-Z]{2})\s+\d{5}")

# Regex to extract zip code from a US formatted address
_ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")


class RetroGameStoreRaw(BaseModel):
    """Raw store record from a retro game store directory."""

    source_id: str
    source: str  # "google_places"
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


def _parse_address_parts(address: str) -> dict[str, str]:
    """Extract street, city, state, zip from a Google Places formatted address.

    Returns a dict with keys street, city, state, zip_code.  Values may be
    empty strings when a component cannot be parsed.
    """
    assert isinstance(address, str), "address must be a str"

    parts = [p.strip() for p in address.split(",")]

    street = parts[0] if len(parts) >= 1 else ""
    city = parts[1] if len(parts) >= 2 else ""

    state = ""
    state_match = _STATE_RE.search(address)
    if state_match is not None:
        state = state_match.group(1)

    zip_code = ""
    zip_match = _ZIP_RE.search(address)
    if zip_match is not None:
        zip_code = zip_match.group(1)

    result = {
        "street": street,
        "city": city,
        "state": state,
        "zip_code": zip_code,
    }
    assert isinstance(result, dict)
    return result


def _convert_google_place(place: GooglePlaceRaw) -> RetroGameStoreRaw | None:
    """Convert a GooglePlaceRaw into a RetroGameStoreRaw.

    Returns None if the address cannot be parsed into required components.
    """
    assert isinstance(place, GooglePlaceRaw), "place must be a GooglePlaceRaw"

    addr = _parse_address_parts(place.address)
    if not addr["street"] or not addr["city"]:
        logger.warning(
            "Could not parse address for place %s (%s), skipping",
            place.place_id,
            place.address,
        )
        return None

    result = RetroGameStoreRaw(
        source_id=place.place_id,
        source="google_places",
        name=place.name,
        street=addr["street"],
        city=addr["city"],
        state=addr["state"],
        zip_code=addr["zip_code"],
        phone=place.phone,
        website=place.website,
        latitude=place.lat,
        longitude=place.lng,
    )
    assert result.source_id == place.place_id
    return result


class RetroGameScraper:
    """Discovers retro game stores via Google Places Text Search.

    Uses retro-gaming-specific search queries across the US and converts
    the results into RetroGameStoreRaw records.
    """

    def __init__(
        self,
        api_key: str,
        delay: float = _REQUEST_DELAY_SECS,
    ) -> None:
        assert isinstance(api_key, str) and len(api_key) > 0, "API key required"
        assert delay >= 0, "Delay must be non-negative"
        self._api_key = api_key
        self._delay = delay
        self._scraper = GooglePlacesScraper(api_key=api_key, delay=delay)

    def fetch_stores(self, max_requests: int | None = None) -> list[RetroGameStoreRaw]:
        """Fetch retro game stores across the US via Google Places Text Search.

        Returns deduplicated list of RetroGameStoreRaw records.
        """
        request_cap = max_requests or _MAX_TOTAL_REQUESTS
        assert request_cap > 0, "max_requests must be positive"

        logger.info(
            "Searching Google Places for retro game stores with %d queries (max %d requests)",
            len(_RETRO_SEARCH_QUERIES),
            request_cap,
        )

        # Use the Google Places scraper with retro-gaming queries
        max_queries = len(_RETRO_SEARCH_QUERIES)
        limit_cells = max(1, request_cap // max(max_queries, 1))

        raw_places = self._scraper.fetch_stores(
            limit_cells=limit_cells,
            max_requests=request_cap,
        )

        # Convert Google Places results to RetroGameStoreRaw
        seen_ids: set[str] = set()
        retro_stores: list[RetroGameStoreRaw] = []

        for place in raw_places:
            converted = _convert_google_place(place)
            if converted is not None and converted.source_id not in seen_ids:
                seen_ids.add(converted.source_id)
                retro_stores.append(converted)

        logger.info(
            "Converted %d Google Places results to %d retro game store records",
            len(raw_places),
            len(retro_stores),
        )
        assert isinstance(retro_stores, list)
        return retro_stores

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._scraper.close()

    def __enter__(self) -> RetroGameScraper:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


def save_raw_to_cache(stores: list[RetroGameStoreRaw], path: Path) -> None:
    """Save parsed retro game stores to a JSON cache file."""
    save_to_cache(stores, path, label="retro game stores")


def load_raw_from_cache(path: Path) -> list[RetroGameStoreRaw]:
    """Load retro game stores from a JSON cache file."""
    return load_from_cache(path, RetroGameStoreRaw, label="retro game stores")
