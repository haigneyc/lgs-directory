"""Platform-specific card search and price extraction."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from urllib.parse import quote_plus

import httpx

from lgs_directory.models.enums import Platform

logger = logging.getLogger(__name__)

_TIMEOUT_SECS = 15
_MAX_PRICE_CANDIDATES = 50  # Upper bound for regex match safety

# Price regex: match $X.XX pattern
_PRICE_PATTERN = re.compile(r"\$(\d{1,4}\.\d{2})")


@dataclass(frozen=True)
class CardSearchResult:
    """Result of searching for a card on a store's website."""

    card_name: str
    found: bool
    store_price: float | None
    product_url: str | None
    extraction_method: str  # "css_selector", "json_ld", "regex", "none"


def build_search_url(base_url: str, card_name: str, platform: Platform | None) -> str:
    """Build a platform-specific search URL for a card name.

    Returns fully-qualified search URL.
    """
    assert isinstance(base_url, str) and len(base_url) > 0
    assert isinstance(card_name, str) and len(card_name) > 0

    clean_base = base_url.rstrip("/")
    encoded_name = quote_plus(card_name)

    if platform == Platform.CRYSTAL_COMMERCE:
        return f"{clean_base}/products/search?q={encoded_name}"

    if platform in (Platform.SHOPIFY, Platform.BINDERPOS):
        return f"{clean_base}/search?q={encoded_name}&type=product"

    if platform == Platform.WOOCOMMERCE:
        return f"{clean_base}/?s={encoded_name}&post_type=product"

    if platform == Platform.SQUARESPACE:
        return f"{clean_base}/search?q={encoded_name}"

    # Generic fallback
    return f"{clean_base}/search?q={encoded_name}"


def extract_price_from_html(
    html: str, card_name: str, platform: Platform | None,
) -> CardSearchResult:
    """Extract card price from search results HTML.

    Platform-specific extraction with generic regex fallback.
    Returns CardSearchResult with price if found.
    """
    assert isinstance(html, str)
    assert isinstance(card_name, str) and len(card_name) > 0

    # Check if card name appears in results at all
    if card_name.lower() not in html.lower():
        return CardSearchResult(
            card_name=card_name,
            found=False,
            store_price=None,
            product_url=None,
            extraction_method="none",
        )

    # Try JSON-LD extraction first (works across platforms)
    json_ld_price = _extract_json_ld_price(html, card_name)
    if json_ld_price is not None:
        return CardSearchResult(
            card_name=card_name,
            found=True,
            store_price=json_ld_price,
            product_url=None,
            extraction_method="json_ld",
        )

    # Platform-specific CSS-based extraction via regex
    platform_price = _extract_platform_price(html, platform)
    if platform_price is not None:
        return CardSearchResult(
            card_name=card_name,
            found=True,
            store_price=platform_price,
            product_url=None,
            extraction_method="css_selector",
        )

    # Generic regex fallback: find $ prices near card name
    regex_price = _extract_regex_price(html, card_name)
    if regex_price is not None:
        return CardSearchResult(
            card_name=card_name,
            found=True,
            store_price=regex_price,
            product_url=None,
            extraction_method="regex",
        )

    # Card name found but no price extracted
    return CardSearchResult(
        card_name=card_name,
        found=True,
        store_price=None,
        product_url=None,
        extraction_method="none",
    )


def _extract_json_ld_price(html: str, card_name: str) -> float | None:
    """Extract price from JSON-LD Product structured data."""
    assert isinstance(html, str)

    # Find JSON-LD blocks
    pattern = re.compile(
        r'<script\s+type=["\']application/ld\+json["\']\s*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )

    for match in pattern.finditer(html[:50_000]):
        try:
            data = json.loads(match.group(1))
            assert isinstance(data, (dict, list))

            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("@type") != "Product":
                    continue

                offers = item.get("offers", {})
                if isinstance(offers, list) and len(offers) > 0:
                    offers = offers[0]
                if not isinstance(offers, dict):
                    continue

                price = offers.get("price")
                if price is not None:
                    return float(price)

        except (json.JSONDecodeError, ValueError, TypeError):
            continue

    return None


def _extract_platform_price(html: str, platform: Platform | None) -> float | None:
    """Extract price using platform-specific HTML patterns."""
    assert isinstance(html, str)

    if platform == Platform.CRYSTAL_COMMERCE:
        # CrystalCommerce: <span class="regular price">$X.XX</span>
        pattern = re.compile(
            r'class=["\'](?:regular\s+)?price["\'][^>]*>\s*\$(\d{1,4}\.\d{2})',
            re.IGNORECASE,
        )
        match = pattern.search(html)
        if match is not None:
            return float(match.group(1))

    if platform in (Platform.SHOPIFY, Platform.BINDERPOS):
        # Shopify: <span class="price">$X.XX</span> or money format
        pattern = re.compile(
            r'class=["\'][^"\']*price[^"\']*["\'][^>]*>\s*\$(\d{1,4}\.\d{2})',
            re.IGNORECASE,
        )
        match = pattern.search(html)
        if match is not None:
            return float(match.group(1))

    if platform == Platform.WOOCOMMERCE:
        # WooCommerce: <span class="woocommerce-Price-amount">$X.XX</span>
        pattern = re.compile(
            r'class=["\']woocommerce-Price-amount[^"\']*["\'][^>]*>'
            r'\s*(?:<[^>]+>)*\s*\$(\d{1,4}\.\d{2})',
            re.IGNORECASE,
        )
        match = pattern.search(html)
        if match is not None:
            return float(match.group(1))

    return None


def _extract_regex_price(html: str, card_name: str) -> float | None:
    """Generic fallback: find $X.XX near the card name in HTML."""
    assert isinstance(html, str)
    assert isinstance(card_name, str)

    # Find card name position, search nearby for prices
    name_lower = card_name.lower()
    html_lower = html.lower()
    name_pos = html_lower.find(name_lower)

    if name_pos == -1:
        return None

    # Search within 500 chars after card name
    search_start = name_pos
    search_end = min(len(html), name_pos + 500)
    nearby_html = html[search_start:search_end]

    prices: list[float] = []
    for match in _PRICE_PATTERN.finditer(nearby_html):
        try:
            price = float(match.group(1))
            # Sanity: MTG cards range from $0.01 to $999
            if 0.01 <= price <= 999.99:
                prices.append(price)
        except ValueError:
            continue

        if len(prices) >= _MAX_PRICE_CANDIDATES:
            break

    if len(prices) == 0:
        return None

    # Return the first reasonable price found
    return prices[0]


def search_card_on_store(
    base_url: str,
    card_name: str,
    platform: Platform | None,
) -> CardSearchResult:
    """Search for a card on a store's website and extract the price.

    Combines URL building, HTTP fetch, and price extraction.
    Returns CardSearchResult.
    """
    assert isinstance(base_url, str) and len(base_url) > 0
    assert isinstance(card_name, str) and len(card_name) > 0

    search_url = build_search_url(base_url, card_name, platform)

    try:
        with httpx.Client(follow_redirects=True, timeout=_TIMEOUT_SECS) as client:
            response = client.get(search_url)
            if response.status_code >= 400:
                return CardSearchResult(
                    card_name=card_name,
                    found=False,
                    store_price=None,
                    product_url=search_url,
                    extraction_method="none",
                )

            html = response.text[:100_000]
            result = extract_price_from_html(html, card_name, platform)

            # Attach the search URL to the result
            return CardSearchResult(
                card_name=result.card_name,
                found=result.found,
                store_price=result.store_price,
                product_url=search_url,
                extraction_method=result.extraction_method,
            )

    except httpx.HTTPError as exc:
        logger.warning("Card search failed for %s on %s: %s", card_name, base_url, exc)
        return CardSearchResult(
            card_name=card_name,
            found=False,
            store_price=None,
            product_url=search_url,
            extraction_method="none",
        )
