"""Freshness detection — how recently a store updated its prices."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT_SECS = 10
_SITEMAP_MAX_BYTES = 50_000
_MAX_TIMESTAMP_PATTERNS = 20  # Upper bound for loop safety

# Patterns for extracting timestamps from page HTML
_UPDATED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(?:prices?\s+updated|last\s+updated|updated\s+on)"
        r"\s*:?\s*(\w+\s+\d{1,2},?\s+\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:prices?\s+updated|last\s+updated|updated\s+on)"
        r"\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:prices?\s+updated|last\s+updated|updated\s+on)"
        r"\s*:?\s*(\d{4}-\d{2}-\d{2})",
        re.IGNORECASE,
    ),
]

# Weak signal: copyright year
_COPYRIGHT_PATTERN = re.compile(r"©\s*(\d{4})")

# Date formats for parsing extracted timestamp strings
_DATE_FORMATS: list[str] = [
    "%B %d, %Y",      # January 15, 2025
    "%B %d %Y",       # January 15 2025
    "%b %d, %Y",      # Jan 15, 2025
    "%b %d %Y",       # Jan 15 2025
    "%m/%d/%Y",       # 01/15/2025
    "%m-%d-%Y",       # 01-15-2025
    "%m/%d/%y",       # 01/15/25
    "%Y-%m-%d",       # 2025-01-15
]


@dataclass(frozen=True)
class FreshnessResult:
    """Result of freshness detection for a store."""

    last_update_detected: datetime | None
    freshness_signals: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0
    method: str = "none"  # "http_header", "sitemap", "page_timestamp", "copyright", "none"


def _check_http_headers(url: str) -> datetime | None:
    """Tier 1: HEAD request for Last-Modified header.

    Returns parsed datetime or None.
    """
    assert isinstance(url, str) and len(url) > 0

    try:
        with httpx.Client(follow_redirects=True, timeout=_TIMEOUT_SECS) as client:
            response = client.head(url)
            if response.status_code >= 400:
                return None

            last_modified = response.headers.get("last-modified")
            if last_modified is None:
                return None

            # Parse HTTP date format (RFC 7231)
            parsed = _parse_http_date(last_modified)
            assert parsed is None or isinstance(parsed, datetime)
            return parsed

    except httpx.HTTPError as exc:
        logger.debug("HEAD request failed for %s: %s", url, exc)
        return None


def _parse_http_date(date_str: str) -> datetime | None:
    """Parse an HTTP Last-Modified date string."""
    assert isinstance(date_str, str)

    http_formats = [
        "%a, %d %b %Y %H:%M:%S %Z",  # RFC 7231
        "%a, %d %b %Y %H:%M:%S GMT",
        "%A, %d-%b-%y %H:%M:%S %Z",   # RFC 850
        "%a %b %d %H:%M:%S %Y",       # asctime
    ]

    for fmt in http_formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.replace(tzinfo=UTC)
        except ValueError:
            continue

    return None


def _check_sitemap(base_url: str) -> datetime | None:
    """Tier 2: Fetch /sitemap.xml and extract max lastmod date.

    Only reads first _SITEMAP_MAX_BYTES to stay cheap.
    Returns most recent lastmod datetime or None.
    """
    assert isinstance(base_url, str) and len(base_url) > 0

    sitemap_url = base_url.rstrip("/") + "/sitemap.xml"

    try:
        with httpx.Client(follow_redirects=True, timeout=_TIMEOUT_SECS) as client:
            response = client.get(sitemap_url)
            if response.status_code != 200:
                return None

            xml_content = response.text[:_SITEMAP_MAX_BYTES]
            assert isinstance(xml_content, str)

            return _parse_sitemap_dates(xml_content)

    except httpx.HTTPError as exc:
        logger.debug("Sitemap fetch failed for %s: %s", sitemap_url, exc)
        return None


def _parse_sitemap_dates(xml_content: str) -> datetime | None:
    """Parse lastmod dates from sitemap XML, return the most recent."""
    assert isinstance(xml_content, str)

    try:
        root = ET.fromstring(xml_content)  # noqa: S314
    except ET.ParseError:
        return None

    # Handle namespace — sitemaps use xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    dates: list[datetime] = []
    lastmod_elements = root.findall(".//sm:lastmod", ns)

    # Also try without namespace
    if len(lastmod_elements) == 0:
        lastmod_elements = root.findall(".//lastmod")

    for elem in lastmod_elements[:_MAX_TIMESTAMP_PATTERNS]:
        text = elem.text
        if text is None:
            continue
        parsed = _parse_iso_date(text.strip())
        if parsed is not None:
            dates.append(parsed)

    if len(dates) == 0:
        return None

    result = max(dates)
    assert isinstance(result, datetime)
    return result


def _parse_iso_date(date_str: str) -> datetime | None:
    """Parse an ISO-ish date string from a sitemap."""
    assert isinstance(date_str, str)

    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
        try:
            parsed = datetime.strptime(date_str, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
        except ValueError:
            continue

    return None


def _extract_page_timestamps(html: str) -> tuple[datetime | None, str]:
    """Tier 3: Regex for 'prices updated on ...', 'last updated: ...', copyright year.

    Returns (datetime, method) where method is 'page_timestamp' or 'copyright'.
    """
    assert isinstance(html, str)

    # Try explicit update patterns first (strong signal)
    for pattern in _UPDATED_PATTERNS:
        match = pattern.search(html[:20_000])
        if match is not None:
            date_str = match.group(1)
            parsed = _parse_page_date(date_str)
            if parsed is not None:
                return parsed, "page_timestamp"

    # Weak signal: copyright year
    copyright_matches = _COPYRIGHT_PATTERN.findall(html[:20_000])
    if len(copyright_matches) > 0:
        try:
            year = int(max(copyright_matches))
            if 2020 <= year <= 2030:
                dt = datetime(year, 1, 1, tzinfo=UTC)
                return dt, "copyright"
        except (ValueError, TypeError):
            pass

    return None, "none"


def _parse_page_date(date_str: str) -> datetime | None:
    """Parse a date string extracted from page content."""
    assert isinstance(date_str, str)

    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.replace(tzinfo=UTC)
        except ValueError:
            continue

    return None


def detect_freshness(url: str, platform: str | None = None) -> FreshnessResult:
    """Run tiered freshness detection on a URL.

    Tiers (cheapest first):
      1. HTTP Last-Modified header (HEAD request)
      2. Sitemap lastmod dates
      3. Page content timestamp extraction

    Returns FreshnessResult with best signal found.
    """
    assert isinstance(url, str) and len(url) > 0

    signals: dict[str, str] = {}

    # Tier 1: HTTP headers
    header_date = _check_http_headers(url)
    if header_date is not None:
        signals["http_last_modified"] = header_date.isoformat()
        return FreshnessResult(
            last_update_detected=header_date,
            freshness_signals=signals,
            confidence=0.70,
            method="http_header",
        )

    # Tier 2: Sitemap
    base_url = _extract_base_url(url)
    sitemap_date = _check_sitemap(base_url)
    if sitemap_date is not None:
        signals["sitemap_lastmod"] = sitemap_date.isoformat()
        return FreshnessResult(
            last_update_detected=sitemap_date,
            freshness_signals=signals,
            confidence=0.60,
            method="sitemap",
        )

    # Tier 3: Page content timestamps — need to fetch the page
    try:
        with httpx.Client(follow_redirects=True, timeout=_TIMEOUT_SECS) as client:
            response = client.get(url)
            if response.status_code < 400:
                html = response.text
                page_date, method = _extract_page_timestamps(html)
                if page_date is not None:
                    confidence = 0.50 if method == "page_timestamp" else 0.20
                    signals[method] = page_date.isoformat()
                    return FreshnessResult(
                        last_update_detected=page_date,
                        freshness_signals=signals,
                        confidence=confidence,
                        method=method,
                    )
    except httpx.HTTPError as exc:
        logger.debug("Page fetch failed for freshness: %s", exc)

    # No signal found
    return FreshnessResult(
        last_update_detected=None,
        freshness_signals=signals,
        confidence=0.0,
        method="none",
    )


def _extract_base_url(url: str) -> str:
    """Extract base URL (scheme + host) from a full URL."""
    assert isinstance(url, str) and len(url) > 0

    # Find the third slash (after scheme://)
    scheme_end = url.find("://")
    if scheme_end == -1:
        return url

    path_start = url.find("/", scheme_end + 3)
    if path_start == -1:
        return url

    return url[:path_start]
