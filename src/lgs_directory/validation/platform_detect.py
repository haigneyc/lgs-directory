"""Platform detection — identify e-commerce platforms from HTML signatures."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from lgs_directory.models.enums import CheckType, Platform
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.validation_log import ValidationLog

logger = logging.getLogger(__name__)

_TIMEOUT_SECS = 15


@dataclass(frozen=True)
class PlatformSignature:
    """A detection signature mapping HTML/header patterns to a platform."""

    platform: Platform
    html_patterns: list[re.Pattern[str]]
    header_patterns: list[tuple[str, re.Pattern[str]]]
    url_patterns: list[re.Pattern[str]]


# Ordered list — first match wins
_SIGNATURES: list[PlatformSignature] = [
    PlatformSignature(
        platform=Platform.CRYSTAL_COMMERCE,
        html_patterns=[
            re.compile(r"crystalcommerce\.com", re.IGNORECASE),
            re.compile(r"cc-product-list", re.IGNORECASE),
        ],
        header_patterns=[],
        url_patterns=[],
    ),
    PlatformSignature(
        platform=Platform.BINDERPOS,
        html_patterns=[
            re.compile(r"binderpos\.com", re.IGNORECASE),
        ],
        header_patterns=[],
        url_patterns=[
            re.compile(r"/products\.json", re.IGNORECASE),
        ],
    ),
    PlatformSignature(
        platform=Platform.SHOPIFY,
        html_patterns=[
            re.compile(r"cdn\.shopify\.com", re.IGNORECASE),
            re.compile(r"Shopify\.theme", re.IGNORECASE),
        ],
        header_patterns=[
            ("x-shopid", re.compile(r"\d+")),
            ("x-shopify-stage", re.compile(r".*")),
        ],
        url_patterns=[],
    ),
    PlatformSignature(
        platform=Platform.WOOCOMMERCE,
        html_patterns=[
            re.compile(r"wc-add-to-cart", re.IGNORECASE),
            re.compile(r"wp-content/plugins/woocommerce", re.IGNORECASE),
        ],
        header_patterns=[],
        url_patterns=[],
    ),
    PlatformSignature(
        platform=Platform.SQUARESPACE,
        html_patterns=[
            re.compile(r"squarespace\.com", re.IGNORECASE),
            re.compile(r"static\d*\.squarespace\.com", re.IGNORECASE),
        ],
        header_patterns=[],
        url_patterns=[],
    ),
    PlatformSignature(
        platform=Platform.WORDPRESS_STRIPE,
        html_patterns=[
            re.compile(r"wp-content", re.IGNORECASE),
        ],
        header_patterns=[],
        url_patterns=[
            re.compile(r"js\.stripe\.com", re.IGNORECASE),
        ],
    ),
]

# TCGPlayer Direct — matched on URL, not HTML
_TCGPLAYER_PATTERN = re.compile(r"store\.tcgplayer\.com", re.IGNORECASE)


def _match_signatures(
    html: str, headers: dict[str, str], url: str
) -> Platform:
    """Match HTML, headers, and URL against platform signatures.

    Returns the first matching Platform, or UNKNOWN.
    """
    assert isinstance(html, str)
    assert isinstance(headers, dict)
    assert isinstance(url, str)

    # Check TCGPlayer Direct first (URL-based)
    if _TCGPLAYER_PATTERN.search(url):
        return Platform.CUSTOM  # TCGPlayer Direct is a marketplace, not a platform

    for sig in _SIGNATURES:
        # Check URL patterns
        for pattern in sig.url_patterns:
            if pattern.search(html) or pattern.search(url):
                # WordPress+Stripe needs BOTH wp-content AND stripe
                if sig.platform == Platform.WORDPRESS_STRIPE:
                    has_wp = any(p.search(html) for p in sig.html_patterns)
                    if not has_wp:
                        continue
                return sig.platform

        # Check HTML patterns
        for pattern in sig.html_patterns:
            if pattern.search(html):
                return sig.platform

        # Check header patterns
        for header_name, pattern in sig.header_patterns:
            header_val = headers.get(header_name.lower(), "")
            if header_val and pattern.search(header_val):
                return sig.platform

    return Platform.UNKNOWN


def detect_platform(url: str) -> Platform:
    """Fetch a URL and detect the e-commerce platform.

    Returns Platform enum value.
    """
    assert isinstance(url, str) and len(url) > 0, "URL must be non-empty"

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=_TIMEOUT_SECS,
        ) as client:
            response = client.get(url)
            response.raise_for_status()

            html = response.text[:50_000]  # First 50k chars
            headers = {k.lower(): v for k, v in response.headers.items()}
            assert isinstance(html, str)

            return _match_signatures(html, headers, url)

    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch %s for platform detection: %s", url, exc)
        return Platform.UNKNOWN


def detect_and_log_platform(
    presence: OnlinePresence,
    session: Session,
) -> Platform:
    """Detect platform for a presence, update it, and log the result.

    Returns the detected Platform.
    """
    assert presence.id is not None, "Presence must be persisted"
    assert presence.url is not None, "Presence must have a URL"

    logger.info("Detecting platform for: %s", presence.url)
    platform = detect_platform(presence.url)

    presence.platform = platform
    presence.last_checked = datetime.now(tz=UTC)

    log = ValidationLog(
        store_id=presence.store_id,
        presence_id=presence.id,
        check_type=CheckType.PLATFORM_DETECT,
        result={"url": presence.url, "platform": platform.value},
    )
    session.add(log)

    logger.info("  → %s", platform.value)
    assert isinstance(platform, Platform)
    return platform
