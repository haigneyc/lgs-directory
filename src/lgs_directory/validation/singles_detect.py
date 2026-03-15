"""MTG singles detection — keyword scan, product sampling, LLM fallback."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from lgs_directory.models.enums import InventorySize, Platform

logger = logging.getLogger(__name__)

_TIMEOUT_SECS = 15
_MAX_PRODUCT_SAMPLES = 5

# Tier 1: Keyword patterns indicating MTG singles
_MTG_KEYWORDS = [
    re.compile(r"magic\s+the\s+gathering", re.IGNORECASE),
    re.compile(r"\bmtg\s+singles?\b", re.IGNORECASE),
    re.compile(r"\bsingle\s+cards?\b", re.IGNORECASE),
    re.compile(r"\bmtg\b.*\bsingles?\b", re.IGNORECASE),
    re.compile(r"\bsingles?\b.*\bmtg\b", re.IGNORECASE),
]

# Tier 2: Card condition/attribute patterns on product pages
_CARD_ATTRIBUTE_PATTERNS = [
    re.compile(r"\b(?:NM|LP|MP|HP|DMG)\b"),  # Conditions
    re.compile(r"\b(?:Near Mint|Lightly Played|Moderately Played)\b", re.IGNORECASE),
    re.compile(r"\bfoil\b", re.IGNORECASE),
    re.compile(r"\b(?:mythic|rare|uncommon|common)\b", re.IGNORECASE),
]

# Known MTG set names (subset for matching)
_SET_NAME_PATTERNS = [
    re.compile(r"\b(?:Modern Horizons|Murders at Karlov Manor|Thunder Junction)\b", re.IGNORECASE),
    re.compile(r"\b(?:Commander|Foundations|Bloomburrow|Duskmourn)\b", re.IGNORECASE),
    re.compile(r"\b(?:Innistrad|Ravnica|Dominaria|Eldraine|Ikoria)\b", re.IGNORECASE),
]

# LLM prompt for classification
_LLM_PROMPT = """Analyze the following HTML snippet from a game store website.
Does this store sell individual Magic: The Gathering cards (singles)?
Respond with ONLY a JSON object: {"sells_singles": true/false, "confidence": 0.0-1.0}

HTML snippet:
{html_snippet}"""


@dataclass(frozen=True)
class SinglesResult:
    """Result of MTG singles detection."""

    sells_mtg_singles: bool
    estimated_inventory_size: InventorySize | None
    confidence: float
    method: str  # "keyword", "product_sample", "llm", "none"


def _keyword_scan(html: str) -> SinglesResult | None:
    """Tier 1: Check for MTG-related keywords in page HTML.

    Returns SinglesResult if strong keyword evidence found, None otherwise.
    """
    assert isinstance(html, str), "html must be a string"

    keyword_hits = 0
    for pattern in _MTG_KEYWORDS:
        if pattern.search(html):
            keyword_hits += 1

    if keyword_hits == 0:
        return None

    # Strong keyword evidence
    if keyword_hits >= 2:
        return SinglesResult(
            sells_mtg_singles=True,
            estimated_inventory_size=InventorySize.MEDIUM,
            confidence=0.85,
            method="keyword",
        )

    # Single keyword — lower confidence
    return SinglesResult(
        sells_mtg_singles=True,
        estimated_inventory_size=InventorySize.SMALL,
        confidence=0.60,
        method="keyword",
    )


def _extract_product_links(html: str, base_url: str) -> list[str]:
    """Extract product page links from HTML.

    Returns up to _MAX_PRODUCT_SAMPLES URLs.
    """
    assert isinstance(html, str)
    assert isinstance(base_url, str)

    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        assert isinstance(href, str)

        # Look for product-like URLs
        if any(kw in href.lower() for kw in ["/product", "/card", "/item", "/p/"]):
            if href.startswith("/"):
                # Strip trailing slash from base, add path
                clean_base = base_url.rstrip("/")
                href = f"{clean_base}{href}"
            if href.startswith("http"):
                links.append(href)

        if len(links) >= _MAX_PRODUCT_SAMPLES:
            break

    assert len(links) <= _MAX_PRODUCT_SAMPLES
    return links


def _sample_products(product_urls: list[str]) -> SinglesResult | None:
    """Tier 2: Fetch product pages and check for card attributes.

    Returns SinglesResult if card-like products found, None otherwise.
    """
    assert isinstance(product_urls, list)

    if len(product_urls) == 0:
        return None

    card_pages = 0
    pages_checked = 0

    with httpx.Client(follow_redirects=True, timeout=_TIMEOUT_SECS) as client:
        for url in product_urls[:_MAX_PRODUCT_SAMPLES]:
            try:
                resp = client.get(url)
                if resp.status_code >= 400:
                    continue

                page_html = resp.text[:20_000]
                pages_checked += 1

                # Check for card attributes
                attr_hits = sum(
                    1 for p in _CARD_ATTRIBUTE_PATTERNS if p.search(page_html)
                )
                set_hits = sum(
                    1 for p in _SET_NAME_PATTERNS if p.search(page_html)
                )

                if attr_hits >= 2 or (attr_hits >= 1 and set_hits >= 1):
                    card_pages += 1

            except httpx.HTTPError:
                continue

    if pages_checked == 0:
        return None

    if card_pages == 0:
        return None

    ratio = card_pages / pages_checked
    assert 0.0 <= ratio <= 1.0

    if ratio >= 0.5:
        return SinglesResult(
            sells_mtg_singles=True,
            estimated_inventory_size=(
                InventorySize.MEDIUM if card_pages >= 3 else InventorySize.SMALL
            ),
            confidence=min(0.95, 0.70 + ratio * 0.25),
            method="product_sample",
        )

    return None


def _llm_classify(
    html: str,
    anthropic_api_key: str,
) -> SinglesResult | None:
    """Tier 3: Use Claude API to classify the page.

    Returns SinglesResult based on LLM response, None on failure.
    """
    assert isinstance(html, str)
    assert isinstance(anthropic_api_key, str) and len(anthropic_api_key) > 0

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=anthropic_api_key)

        # Truncate HTML for the LLM
        snippet = html[:3000]
        prompt = _LLM_PROMPT.format(html_snippet=snippet)

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text
        assert isinstance(response_text, str)

        # Parse JSON response
        import json
        result = json.loads(response_text)
        assert isinstance(result, dict)

        sells = result.get("sells_singles", False)
        confidence = float(result.get("confidence", 0.5))

        return SinglesResult(
            sells_mtg_singles=bool(sells),
            estimated_inventory_size=InventorySize.SMALL if sells else InventorySize.NONE,
            confidence=confidence,
            method="llm",
        )

    except Exception as exc:
        logger.warning("LLM classification failed: %s", exc)
        return None


def detect_singles(
    url: str,
    platform: Platform | None,
    *,
    anthropic_api_key: str | None = None,
    budget_remaining_cents: int = 500,
) -> SinglesResult:
    """Detect if a store website sells MTG singles.

    Three-tier detection:
      1. Keyword scan of main page
      2. Product page sampling
      3. LLM fallback (budget-capped)

    Returns SinglesResult with detection outcome.
    """
    assert isinstance(url, str) and len(url) > 0
    assert budget_remaining_cents >= 0

    # Fetch main page
    try:
        with httpx.Client(follow_redirects=True, timeout=_TIMEOUT_SECS) as client:
            response = client.get(url)
            if response.status_code >= 400:
                return SinglesResult(
                    sells_mtg_singles=False,
                    estimated_inventory_size=None,
                    confidence=0.0,
                    method="none",
                )
            html = response.text
    except httpx.HTTPError:
        return SinglesResult(
            sells_mtg_singles=False,
            estimated_inventory_size=None,
            confidence=0.0,
            method="none",
        )

    assert isinstance(html, str)

    # Tier 1: Keyword scan
    result = _keyword_scan(html)
    if result is not None and result.confidence >= 0.80:
        return result

    # Tier 2: Product page sampling
    product_links = _extract_product_links(html, url)
    if len(product_links) > 0:
        sample_result = _sample_products(product_links)
        if sample_result is not None:
            return sample_result

    # Tier 3: LLM fallback (if budget allows and key available)
    if anthropic_api_key and budget_remaining_cents >= 5:
        llm_result = _llm_classify(html, anthropic_api_key)
        if llm_result is not None:
            return llm_result

    # If tier 1 found a low-confidence keyword match, return it
    if result is not None:
        return result

    # No detection
    return SinglesResult(
        sells_mtg_singles=False,
        estimated_inventory_size=InventorySize.NONE,
        confidence=0.5,
        method="none",
    )
