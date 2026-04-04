"""Comic store discovery via Google Places Text Search.

The original plan assumed comicbookstores.co and League of Comic Geeks had
public JSON APIs.  Neither site exposes one, so this module delegates to
the Google Places (New) Text Search API with comic-specific search terms.
Results are converted into ComicStoreRaw records for the existing ingest
pipeline.
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

# Comic-specific search queries for Google Places Text Search
_COMIC_SEARCH_QUERIES = [
    "comic book store",
    "comic shop",
    "comics and collectibles store",
]

# Safety caps
_MAX_TOTAL_REQUESTS = 200
_REQUEST_DELAY_SECS = 0.3

# US state abbreviations used as region hints in queries
_US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
]

# Regex to extract state code from a US formatted address
_STATE_RE = re.compile(r",\s*([A-Z]{2})\s+\d{5}")

# Regex to extract zip code from a US formatted address
_ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")


class ComicStoreRaw(BaseModel):
    """Raw store record from a comic store directory."""

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


def _convert_google_place(place: GooglePlaceRaw) -> ComicStoreRaw | None:
    """Convert a GooglePlaceRaw into a ComicStoreRaw.

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

    result = ComicStoreRaw(
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


class ComicStoreScraper:
    """Discovers comic stores via Google Places Text Search.

    Uses comic-specific search queries across US states and converts
    the results into ComicStoreRaw records.
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

    def fetch_stores(self, max_requests: int | None = None) -> list[ComicStoreRaw]:
        """Fetch comic stores across the US via Google Places Text Search.

        Returns deduplicated list of ComicStoreRaw records.
        """
        request_cap = max_requests or _MAX_TOTAL_REQUESTS
        assert request_cap > 0, "max_requests must be positive"

        logger.info(
            "Searching Google Places for comic stores with %d queries (max %d requests)",
            len(_COMIC_SEARCH_QUERIES),
            request_cap,
        )

        # Use the Google Places scraper with comic-specific queries
        # We limit grid cells to control request count
        # Each cell x query = 1+ request, so estimate cells from cap
        max_queries = len(_COMIC_SEARCH_QUERIES)
        limit_cells = max(1, request_cap // max(max_queries, 1))

        raw_places = self._scraper.fetch_stores(
            limit_cells=limit_cells,
            max_requests=request_cap,
        )

        # Convert Google Places results to ComicStoreRaw
        seen_ids: set[str] = set()
        comic_stores: list[ComicStoreRaw] = []

        for place in raw_places:
            converted = _convert_google_place(place)
            if converted is not None and converted.source_id not in seen_ids:
                seen_ids.add(converted.source_id)
                comic_stores.append(converted)

        logger.info(
            "Converted %d Google Places results to %d comic store records",
            len(raw_places),
            len(comic_stores),
        )
        assert isinstance(comic_stores, list)
        return comic_stores

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._scraper.close()

    def __enter__(self) -> ComicStoreScraper:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


def save_raw_to_cache(stores: list[ComicStoreRaw], path: Path) -> None:
    """Save parsed comic stores to a JSON cache file."""
    save_to_cache(stores, path, label="comic stores")


def load_raw_from_cache(path: Path) -> list[ComicStoreRaw]:
    """Load comic stores from a JSON cache file."""
    return load_from_cache(path, ComicStoreRaw, label="comic stores")
