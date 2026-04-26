"""OpenStreetMap Overpass API discovery for LGS — per-state queries.

Mirrors the LFS branch ``feat/osm-overpass-discovery`` plumbing
(``lfs_locator/discovery/osm_overpass.py``) with three differences:

* the discovery query asks for game/comic/hobby/toy shop tags rather
  than fish/aquarium/pet tags;
* one query per state ISO-3166-2 admin area instead of a single
  continental-US bbox;
* downstream classification lives in ``quality_filters.classify_osm_candidate``
  rather than a sibling ``lfs_filter`` module.

Endpoint history: the ``reference_overpass_kumi_mirror.md`` standing
memory recommended ``https://overpass.kumi.systems/api/interpreter``
as the mandatory primary. As of 2026-04-25 the kumi domain is hosted
by Private.coffee and the ``/api/interpreter`` route returns HTTP 404
for every request (the migration broke the v1 endpoint). The Swiss
community mirror at ``overpass.osm.ch`` answers HTTP 200 but returns
zero elements for every query (probable stale/empty index). Until a
new kumi-equivalent appears we use the official upstream
(``https://overpass-api.de/api/interpreter``) as primary and the
load-balanced ``https://lz4.overpass-api.de/api/interpreter`` as the
single-shot fallback. Both endpoints round-tripped successfully with
the same ``data=...`` POST body the kumi client used. Update the
standing memory once a stable third-party mirror reappears.
"""

from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Primary endpoint: the official Overpass upstream. Replaces the kumi
# mirror named in the spec — see the module docstring.
_OVERPASS_PRIMARY_URL = "https://overpass-api.de/api/interpreter"
# Load-balanced sibling endpoint (lz4 frontend). Probed clean
# 2026-04-25 with the same query body.
_OVERPASS_FALLBACK_URL = "https://lz4.overpass-api.de/api/interpreter"

# overpass-api.de's mod_security rejects ``python-httpx/*`` with HTTP
# 406. A descriptive UA string identifying the project + contact is
# the documented Overpass etiquette.
_OVERPASS_USER_AGENT = (
    "lgs-directory-osm-state/0.1 (+https://rollforstore.com; "
    "chris.haigney@gmail.com)"
)

# Server-side query timeout (seconds). 180 is the largest the public
# Overpass instance will honour; kumi follows the same convention.
_QUERY_TIMEOUT_SECS = 180

# Polite delay between consecutive state queries when a single CLI
# invocation processes more than one state.
_INTER_STATE_DELAY_SECS = 5.0

# Hard cap on the number of elements parsed from a single response
# (defensive against pathological responses; legitimate state pulls
# top out around 1–3 k entries).
_MAX_ELEMENTS = 100_000

# Retry schedule for transient Overpass failures (429, network errors,
# 5xx). Mirrors the LFS branch's hardening of the same client.
_RETRY_BACKOFF_SECS: tuple[float, float, float] = (15.0, 30.0, 60.0)
_MAX_RETRY_JITTER_SECS = 5.0

# OSM shop tag values queried per state. The 3-tier classifier in
# ``quality_filters.classify_osm_candidate`` decides what to do with
# each result (AUTO_ACCEPT / CANDIDATE_QUEUE / AUTO_REJECT). Keeping
# the query broad and the classifier strict matches the spec's
# "recall-first" stance.
_LGS_SHOP_TAG_VALUES: tuple[str, ...] = (
    "games",
    "comics",
    "anime",
    "collector",
    "hobby",
    "video_games",
    "toys",
)


class OsmPlaceRaw(BaseModel):
    """Raw place record parsed from an Overpass element."""

    osm_id: int
    osm_type: str  # "node" or "way"
    name: str
    street: str | None = None
    city: str | None = None
    state: str | None = None
    postcode: str | None = None
    phone: str | None = None
    website: str | None = None
    lat: float | None = None
    lng: float | None = None
    opening_hours: str | None = None
    shop_type: str | None = None  # value of the ``shop=`` tag


@dataclass(frozen=True)
class OverpassFetchStats:
    """Counters from the most recent Overpass call."""

    raw_elements: int = 0
    parsed: int = 0
    skipped_no_name: int = 0
    fallback_used: bool = False
    elapsed_secs: float = 0.0


def _state_iso(state_code: str) -> str:
    """Return the canonical ``US-XX`` ISO-3166-2 code for a 2-letter state."""
    assert isinstance(state_code, str), "state_code must be a string"
    assert len(state_code) == 2, "state_code must be 2 letters"

    upper = state_code.upper()
    assert upper.isalpha(), f"state_code must be alphabetic, got {state_code!r}"
    return f"US-{upper}"


def _build_overpass_query(state_code: str) -> str:
    """Build the per-state Overpass QL query.

    Args:
        state_code: 2-letter US state code (e.g. ``"CO"``). DC is also
            valid via ISO-3166-2 ``US-DC``.

    Returns:
        A complete Overpass QL query string.
    """
    assert isinstance(state_code, str)
    iso = _state_iso(state_code)

    tag_lines: list[str] = []
    cap = min(len(_LGS_SHOP_TAG_VALUES), 32)
    for i in range(cap):
        tag = _LGS_SHOP_TAG_VALUES[i]
        tag_lines.append(f'  node["shop"="{tag}"](area.s);')
        tag_lines.append(f'  way["shop"="{tag}"](area.s);')
    tag_block = "\n".join(tag_lines)

    query = (
        f"[out:json][timeout:{_QUERY_TIMEOUT_SECS}];\n"
        f'area["ISO3166-2"="{iso}"][admin_level=4]->.s;\n'
        f"(\n{tag_block}\n);\n"
        f"out center tags;\n"
    )
    assert "area.s" in query
    return query


def _compute_retry_delay(attempt: int) -> float:
    """Return bounded retry delay with small positive jitter."""
    assert isinstance(attempt, int), "attempt must be an int"
    assert 0 <= attempt < len(_RETRY_BACKOFF_SECS), "attempt out of range"

    base = _RETRY_BACKOFF_SECS[attempt]
    jitter_cap = min(_MAX_RETRY_JITTER_SECS, base * 0.25)
    jitter = random.uniform(0.0, jitter_cap)
    wait = base + jitter
    assert wait >= base, "jitter must not reduce the delay"
    return wait


def _parse_element(elem: dict[str, Any]) -> OsmPlaceRaw | None:
    """Parse a single Overpass element. Returns None when the name is empty."""
    assert isinstance(elem, dict), "element must be a dict"

    tags = elem.get("tags", {})
    if not isinstance(tags, dict):
        return None

    name = str(tags.get("name", "")).strip()
    if not name:
        return None

    osm_type = str(elem.get("type", "node"))
    osm_id = int(elem.get("id", 0))

    lat: float | None = None
    lng: float | None = None
    if osm_type == "node":
        lat_val = elem.get("lat")
        lng_val = elem.get("lon")
        lat = float(lat_val) if isinstance(lat_val, (int, float)) else None
        lng = float(lng_val) if isinstance(lng_val, (int, float)) else None
    elif osm_type == "way":
        center = elem.get("center", {})
        if isinstance(center, dict):
            lat_val = center.get("lat")
            lng_val = center.get("lon")
            lat = float(lat_val) if isinstance(lat_val, (int, float)) else None
            lng = float(lng_val) if isinstance(lng_val, (int, float)) else None

    shop_tag = tags.get("shop")
    shop_type = str(shop_tag).strip().lower() if isinstance(shop_tag, str) else None

    state_val = tags.get("addr:state")
    state_norm = (
        str(state_val).strip().upper()[:2] if isinstance(state_val, str) else None
    )

    return OsmPlaceRaw(
        osm_id=osm_id,
        osm_type=osm_type,
        name=name,
        street=tags.get("addr:street"),
        city=tags.get("addr:city"),
        state=state_norm,
        postcode=tags.get("addr:postcode"),
        phone=tags.get("phone") or tags.get("contact:phone"),
        website=tags.get("website") or tags.get("contact:website"),
        lat=lat,
        lng=lng,
        opening_hours=tags.get("opening_hours"),
        shop_type=shop_type,
    )


class OverpassClient:
    """Per-state Overpass fetcher with kumi-mirror primary + retry."""

    def __init__(
        self,
        *,
        primary_url: str = _OVERPASS_PRIMARY_URL,
        fallback_url: str = _OVERPASS_FALLBACK_URL,
        inter_state_delay_secs: float = _INTER_STATE_DELAY_SECS,
    ) -> None:
        assert isinstance(primary_url, str) and primary_url.startswith("http")
        assert isinstance(fallback_url, str) and fallback_url.startswith("http")
        assert inter_state_delay_secs >= 0

        self._primary_url = primary_url
        self._fallback_url = fallback_url
        self._inter_state_delay_secs = inter_state_delay_secs
        self._client: httpx.Client | None = None
        self.last_fetch_stats: OverpassFetchStats = OverpassFetchStats()

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=_QUERY_TIMEOUT_SECS + 30,
                headers={"User-Agent": _OVERPASS_USER_AGENT},
            )
        assert self._client is not None
        return self._client

    def _post(self, url: str, query: str) -> list[dict[str, Any]]:
        """Single POST. Raises HTTPStatusError / RequestError on failure."""
        assert isinstance(url, str) and url.startswith("http")
        assert isinstance(query, str) and len(query) > 0

        client = self._get_client()
        response = client.post(
            url,
            data={"data": query},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()

        data = response.json()
        assert isinstance(data, dict), "Overpass response must be a JSON object"
        elements = data.get("elements", [])
        assert isinstance(elements, list), "Overpass elements must be a list"
        return elements

    def _fetch_with_retry(
        self, url: str, query: str, label: str,
    ) -> list[dict[str, Any]]:
        """POST with bounded retries on 429 / network / 5xx errors."""
        assert isinstance(label, str) and len(label) > 0
        max_retries = len(_RETRY_BACKOFF_SECS)
        assert max_retries > 0

        for attempt in range(max_retries):
            try:
                return self._post(url, query)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                retriable = status == 429 or 500 <= status < 600
                if not retriable or attempt >= max_retries - 1:
                    raise
                wait = _compute_retry_delay(attempt)
                logger.warning(
                    "Overpass %s HTTP %d on %s, waiting %.1fs (attempt %d/%d)",
                    url, status, label, wait, attempt + 1, max_retries,
                )
                time.sleep(wait)
            except httpx.RequestError as exc:
                if attempt >= max_retries - 1:
                    raise
                wait = _compute_retry_delay(attempt)
                logger.warning(
                    "Overpass %s network error on %s (%s: %s), "
                    "waiting %.1fs (attempt %d/%d)",
                    url, label, type(exc).__name__, exc, wait,
                    attempt + 1, max_retries,
                )
                time.sleep(wait)

        raise AssertionError("unreachable: retry loop exited without return")

    def fetch_state(self, state_code: str) -> list[OsmPlaceRaw]:
        """Fetch and parse OSM elements for a single US state.

        Tries the kumi mirror first; on exhaustion of retries falls back
        to the public Overpass endpoint exactly once. Returns the parsed
        candidate list. Downstream tier classification is the caller's
        job.
        """
        assert isinstance(state_code, str), "state_code must be a string"
        assert len(state_code) == 2, "state_code must be 2 letters"

        query = _build_overpass_query(state_code)
        label = f"state={state_code.upper()}"
        start = time.monotonic()
        fallback_used = False
        elements: list[dict[str, Any]]

        try:
            elements = self._fetch_with_retry(self._primary_url, query, label)
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning(
                "Primary Overpass mirror exhausted for %s (%s: %s) — "
                "trying public fallback once",
                label, type(exc).__name__, exc,
            )
            fallback_used = True
            elements = self._fetch_with_retry(self._fallback_url, query, label)

        elapsed = time.monotonic() - start
        cap = min(len(elements), _MAX_ELEMENTS)
        parsed: list[OsmPlaceRaw] = []
        skipped_no_name = 0
        for i in range(cap):
            place = _parse_element(elements[i])
            if place is None:
                skipped_no_name += 1
                continue
            parsed.append(place)

        self.last_fetch_stats = OverpassFetchStats(
            raw_elements=len(elements),
            parsed=len(parsed),
            skipped_no_name=skipped_no_name,
            fallback_used=fallback_used,
            elapsed_secs=elapsed,
        )
        logger.info(
            "Overpass %s: raw=%d parsed=%d skipped=%d fallback=%s in %.2fs",
            label, len(elements), len(parsed), skipped_no_name,
            fallback_used, elapsed,
        )
        return parsed

    def sleep_between_states(self) -> None:
        """Polite delay between back-to-back state queries."""
        if self._inter_state_delay_secs > 0:
            time.sleep(self._inter_state_delay_secs)

    def close(self) -> None:
        """Release the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            self._client.close()


def save_raw_to_cache(stores: list[OsmPlaceRaw], path: Path) -> None:
    """Write parsed OSM stores to a JSON cache file."""
    assert isinstance(path, Path), "path must be a Path"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [s.model_dump() for s in stores]
    path.write_text(json.dumps(data, indent=2))
    assert path.exists()
    logger.info("Saved %d OSM stores to %s", len(data), path)


def load_raw_from_cache(path: Path) -> list[OsmPlaceRaw]:
    """Load OSM stores from a JSON cache file."""
    assert isinstance(path, Path), "path must be a Path"
    assert path.exists(), f"Cache file not found: {path}"
    data = json.loads(path.read_text())
    assert isinstance(data, list), "Cache data must be a list"
    stores = [OsmPlaceRaw.model_validate(item) for item in data]
    logger.info("Loaded %d OSM stores from %s", len(stores), path)
    return stores
