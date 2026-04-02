"""Website content extraction — description, products, and events."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_TIMEOUT_SECS = 15
_MAX_REDIRECTS = 5
_MAX_HTML_LEN = 50_000
_MAX_EVENT_LINKS = 20
_MAX_PRODUCT_KEYWORDS = 50

# Product category keyword patterns
_PRODUCT_PATTERNS: list[tuple[str, list[re.Pattern[str]]]] = [
    ("mtg", [
        re.compile(r"magic\s*:?\s*the\s+gathering", re.IGNORECASE),
        re.compile(r"\bmtg\b", re.IGNORECASE),
    ]),
    ("pokemon", [
        re.compile(r"pok[eé]mon", re.IGNORECASE),
    ]),
    ("yugioh", [
        re.compile(r"yu[\-\s]?gi[\-\s]?oh", re.IGNORECASE),
    ]),
    ("fab", [
        re.compile(r"flesh\s+and\s+blood", re.IGNORECASE),
    ]),
    ("board_games", [
        re.compile(r"board\s+games?", re.IGNORECASE),
        re.compile(r"tabletop\s+games?", re.IGNORECASE),
    ]),
    ("dnd", [
        re.compile(r"dungeons?\s*&?\s*dragons?", re.IGNORECASE),
        re.compile(r"\bd&d\b", re.IGNORECASE),
        re.compile(r"\brpgs?\b", re.IGNORECASE),
        re.compile(r"pathfinder", re.IGNORECASE),
    ]),
    ("miniatures", [
        re.compile(r"miniatures?", re.IGNORECASE),
        re.compile(r"warhammer", re.IGNORECASE),
        re.compile(r"40k\b", re.IGNORECASE),
    ]),
    ("comics", [
        re.compile(r"\bcomics?\b", re.IGNORECASE),
        re.compile(r"graphic\s+novels?", re.IGNORECASE),
    ]),
]

# Event-related URL path patterns
_EVENT_PATH_PATTERNS = [
    re.compile(r"/events?(?:[/\?#]|$)", re.IGNORECASE),
    re.compile(r"/calendar(?:[/\?#]|$)", re.IGNORECASE),
    re.compile(r"/schedule(?:[/\?#]|$)", re.IGNORECASE),
    re.compile(r"/tournaments?(?:[/\?#]|$)", re.IGNORECASE),
]

# Event-related text patterns
_EVENT_TEXT_PATTERNS = [
    re.compile(r"friday\s+night\s+magic", re.IGNORECASE),
    re.compile(r"\bfnm\b", re.IGNORECASE),
    re.compile(r"event\s+schedule", re.IGNORECASE),
    re.compile(r"upcoming\s+events?", re.IGNORECASE),
    re.compile(r"weekly\s+events?", re.IGNORECASE),
    re.compile(r"tournament\s+schedule", re.IGNORECASE),
    re.compile(r"in[\-\s]store\s+events?", re.IGNORECASE),
    re.compile(r"prerelease", re.IGNORECASE),
]

# LLM prompt for product/content extraction
_LLM_PROMPT = """Analyze the following HTML snippet from a local game store website.
Extract what products/games this store carries.

Respond with ONLY a JSON object:
{
  "products": ["mtg", "pokemon", "yugioh", "fab", "board_games", "dnd", "miniatures", "comics"],
  "confidence": 0.0-1.0
}

Only include products you find evidence for. Valid keys: mtg, pokemon, yugioh, fab, board_games, dnd, miniatures, comics.

HTML snippet:
{html_snippet}"""

_VALID_PRODUCTS = frozenset(
    ["mtg", "pokemon", "yugioh", "fab", "board_games", "dnd", "miniatures", "comics"]
)


@dataclass(frozen=True)
class ContentResult:
    """Result of website content extraction."""

    description: str | None  # 1-3 sentence store description
    products: list[str]  # e.g., ["mtg", "pokemon", "board_games", "dnd"]
    has_events: bool  # whether the store appears to host events
    event_url: str | None  # URL to events page if found
    confidence: float  # 0.0-1.0
    method: str  # "keyword", "llm", "none"


def _extract_description(soup: BeautifulSoup) -> str | None:
    """Extract a short store description from parsed HTML.

    Checks meta description first, then falls back to first meaningful paragraph.
    Returns a trimmed string or None.
    """
    assert soup is not None, "soup must not be None"

    # Try meta description
    meta = soup.find("meta", attrs={"name": "description"})
    if meta is not None:
        content = meta.get("content", "")
        assert isinstance(content, str), "meta content must be a string"
        stripped = content.strip()
        if len(stripped) > 20:
            # Truncate to ~300 chars on sentence boundary
            return _truncate_description(stripped)

    # Try og:description
    og_meta = soup.find("meta", attrs={"property": "og:description"})
    if og_meta is not None:
        content = og_meta.get("content", "")
        assert isinstance(content, str), "og:description content must be a string"
        stripped = content.strip()
        if len(stripped) > 20:
            return _truncate_description(stripped)

    # Fall back to first meaningful <p> tag
    paragraphs = soup.find_all("p", limit=20)
    for p_tag in paragraphs:
        text = p_tag.get_text(strip=True)
        assert isinstance(text, str), "paragraph text must be a string"
        if len(text) > 40:
            return _truncate_description(text)

    return None


def _truncate_description(text: str) -> str:
    """Truncate description to ~300 characters on a sentence boundary."""
    assert isinstance(text, str), "text must be a string"
    assert len(text) > 0, "text must not be empty"

    if len(text) <= 300:
        return text

    # Find last sentence end within 300 chars
    truncated = text[:300]
    last_period = truncated.rfind(".")
    if last_period > 100:
        return truncated[: last_period + 1]

    return truncated.rstrip() + "..."


def _keyword_scan_products(html: str) -> list[str]:
    """Scan HTML for product category keywords.

    Returns a list of detected product category keys.
    """
    assert isinstance(html, str), "html must be a string"

    products: list[str] = []
    scan_count = 0

    for category, patterns in _PRODUCT_PATTERNS:
        if scan_count >= _MAX_PRODUCT_KEYWORDS:
            break

        for pattern in patterns:
            scan_count += 1
            if pattern.search(html):
                products.append(category)
                break  # One match per category is enough

    assert all(p in _VALID_PRODUCTS for p in products), "all products must be valid"
    return products


def _find_event_url(soup: BeautifulSoup, base_url: str) -> str | None:
    """Search for an events page link in the parsed HTML.

    Returns the first matching event URL or None.
    """
    assert soup is not None, "soup must not be None"
    assert isinstance(base_url, str), "base_url must be a string"

    links_checked = 0
    for a_tag in soup.find_all("a", href=True):
        if links_checked >= _MAX_EVENT_LINKS:
            break
        links_checked += 1

        href = a_tag["href"]
        assert isinstance(href, str), "href must be a string"

        for pattern in _EVENT_PATH_PATTERNS:
            if pattern.search(href):
                if href.startswith("/"):
                    clean_base = base_url.rstrip("/")
                    return f"{clean_base}{href}"
                if href.startswith("http"):
                    return href

    return None


def _detect_events(html: str, soup: BeautifulSoup, base_url: str) -> tuple[bool, str | None]:
    """Detect whether the store hosts events and find the events URL.

    Returns (has_events, event_url).
    """
    assert isinstance(html, str), "html must be a string"
    assert soup is not None, "soup must not be None"

    # Check for event URL in links
    event_url = _find_event_url(soup, base_url)
    if event_url is not None:
        return True, event_url

    # Check for event text patterns in HTML
    for pattern in _EVENT_TEXT_PATTERNS:
        if pattern.search(html):
            return True, None

    return False, None


def _llm_extract_products(
    html: str,
    anthropic_api_key: str,
) -> list[str] | None:
    """Use Claude Haiku to extract product categories from HTML.

    Returns a list of product keys, or None on failure.
    """
    assert isinstance(html, str), "html must be a string"
    assert isinstance(anthropic_api_key, str) and len(anthropic_api_key) > 0

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=anthropic_api_key)

        snippet = html[:3000]
        prompt = _LLM_PROMPT.format(html_snippet=snippet)

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text
        assert isinstance(response_text, str), "LLM response must be a string"

        result = json.loads(response_text)
        assert isinstance(result, dict), "LLM response must be a dict"

        raw_products = result.get("products", [])
        assert isinstance(raw_products, list), "products must be a list"

        # Filter to valid product keys only
        products = [p for p in raw_products if p in _VALID_PRODUCTS]
        return products

    except Exception as exc:
        logger.warning("LLM content extraction failed: %s", exc)
        return None


def extract_content(
    url: str,
    *,
    anthropic_api_key: str | None = None,
    llm_budget_cents: int = 500,
) -> ContentResult:
    """Extract description, products, and event info from a store website.

    Two-tier detection:
      1. Keyword scan of page HTML for products/events
      2. LLM fallback for product extraction (budget-capped)

    Returns ContentResult with extraction outcome.
    """
    assert isinstance(url, str) and len(url) > 0, "URL must be non-empty"
    assert llm_budget_cents >= 0, "budget must be non-negative"

    # Fetch the page
    try:
        with httpx.Client(
            follow_redirects=True,
            max_redirects=_MAX_REDIRECTS,
            timeout=_TIMEOUT_SECS,
        ) as client:
            response = client.get(url)
            if response.status_code >= 400:
                return ContentResult(
                    description=None,
                    products=[],
                    has_events=False,
                    event_url=None,
                    confidence=0.0,
                    method="none",
                )
            html = response.text[:_MAX_HTML_LEN]
    except httpx.HTTPError:
        return ContentResult(
            description=None,
            products=[],
            has_events=False,
            event_url=None,
            confidence=0.0,
            method="none",
        )

    assert isinstance(html, str), "html must be a string"

    soup = BeautifulSoup(html, "html.parser")

    # Extract description
    description = _extract_description(soup)

    # Detect events
    has_events, event_url = _detect_events(html, soup, url)

    # Tier 1: Keyword scan for products
    products = _keyword_scan_products(html)

    if len(products) >= 2:
        return ContentResult(
            description=description,
            products=products,
            has_events=has_events,
            event_url=event_url,
            confidence=0.80,
            method="keyword",
        )

    # Tier 2: LLM fallback if keywords are inconclusive
    if anthropic_api_key and llm_budget_cents >= 5:
        llm_products = _llm_extract_products(html, anthropic_api_key)
        if llm_products is not None and len(llm_products) > 0:
            # Merge keyword hits with LLM results (LLM may find more)
            merged = list(set(products + llm_products))
            return ContentResult(
                description=description,
                products=merged,
                has_events=has_events,
                event_url=event_url,
                confidence=0.70,
                method="llm",
            )

    # Return whatever keywords found (even if few)
    if len(products) > 0:
        return ContentResult(
            description=description,
            products=products,
            has_events=has_events,
            event_url=event_url,
            confidence=0.50,
            method="keyword",
        )

    return ContentResult(
        description=description,
        products=[],
        has_events=has_events,
        event_url=event_url,
        confidence=0.30,
        method="none",
    )
