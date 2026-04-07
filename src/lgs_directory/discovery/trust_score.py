"""Trust score calculation for stores.

Calculates a 0-100 trust score for each store based on positive and
negative signals. Higher scores indicate more trusted/verified stores.

Score components:
  +40  WPN registered (has wpn_id)
  +25  Content scraper found game products (products > 0)
  +15  Content scraper confidence >= 0.7
  +10  Has a website URL
  +5   Has a phone number
  +5   Has Google Place ID match
  -20  Content scraper found 0 products with confidence < 0.5
  -10  Only discovered via google_places (no other source)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Score component weights
_SCORE_WPN_REGISTERED = 40
_SCORE_CONTENT_PRODUCTS = 25
_SCORE_CONTENT_HIGH_CONFIDENCE = 15
_SCORE_HAS_WEBSITE = 10
_SCORE_HAS_PHONE = 5
_SCORE_HAS_GOOGLE_PLACE_ID = 5
_PENALTY_LOW_CONTENT = -20
_PENALTY_GOOGLE_ONLY = -10

# Thresholds
_HIGH_CONFIDENCE_THRESHOLD = 0.7
_LOW_CONFIDENCE_THRESHOLD = 0.5

# Bounds
_MIN_SCORE = 0
_MAX_SCORE = 100
_MAX_SIGNALS = 20


@dataclass(frozen=True)
class TrustResult:
    """Result of trust score calculation for a store."""

    score: int
    signals: list[str]


def calculate_trust_score(
    wpn_id: str | None,
    has_website: bool,
    has_phone: bool,
    google_place_id: str | None,
    discovery_source: str,
    content_products: list[str] | None,
    content_confidence: float | None,
) -> TrustResult:
    """Calculate a trust score for a store based on available signals.

    Args:
        wpn_id: WPN identifier if store is WPN-registered.
        has_website: Whether the store has a website URL on file.
        has_phone: Whether the store has a phone number.
        google_place_id: Google Place ID if matched.
        discovery_source: How the store was discovered (e.g. 'wpn', 'google_places').
        content_products: List of product categories from content scraper, or None.
        content_confidence: Content scraper confidence (0.0-1.0), or None.

    Returns:
        TrustResult with score (0-100) and list of signal descriptions.
    """
    assert isinstance(has_website, bool), "has_website must be a bool"
    assert isinstance(has_phone, bool), "has_phone must be a bool"
    assert isinstance(discovery_source, str), "discovery_source must be a string"

    raw_score = 0
    signals: list[str] = []

    # Positive: WPN registered
    if wpn_id is not None and len(wpn_id) > 0:
        raw_score += _SCORE_WPN_REGISTERED
        signals.append(f"+{_SCORE_WPN_REGISTERED} wpn_registered")

    # Positive: Content scraper found products
    product_count = len(content_products) if content_products is not None else 0
    if product_count > 0:
        raw_score += _SCORE_CONTENT_PRODUCTS
        signals.append(f"+{_SCORE_CONTENT_PRODUCTS} content_products({product_count})")

    # Positive: Content scraper high confidence
    if content_confidence is not None and content_confidence >= _HIGH_CONFIDENCE_THRESHOLD:
        raw_score += _SCORE_CONTENT_HIGH_CONFIDENCE
        signals.append(
            f"+{_SCORE_CONTENT_HIGH_CONFIDENCE} content_confidence({content_confidence:.2f})"
        )

    # Positive: Has website
    if has_website:
        raw_score += _SCORE_HAS_WEBSITE
        signals.append(f"+{_SCORE_HAS_WEBSITE} has_website")

    # Positive: Has phone
    if has_phone:
        raw_score += _SCORE_HAS_PHONE
        signals.append(f"+{_SCORE_HAS_PHONE} has_phone")

    # Positive: Has Google Place ID
    if google_place_id is not None and len(google_place_id) > 0:
        raw_score += _SCORE_HAS_GOOGLE_PLACE_ID
        signals.append(f"+{_SCORE_HAS_GOOGLE_PLACE_ID} has_google_place_id")

    # Penalty: Low content confidence with no products
    if (
        content_confidence is not None
        and content_confidence < _LOW_CONFIDENCE_THRESHOLD
        and product_count == 0
    ):
        raw_score += _PENALTY_LOW_CONTENT
        signals.append(f"{_PENALTY_LOW_CONTENT} low_content_confidence({content_confidence:.2f})")

    # Penalty: Only discovered via Google Places
    if discovery_source == "google_places":
        raw_score += _PENALTY_GOOGLE_ONLY
        signals.append(f"{_PENALTY_GOOGLE_ONLY} google_places_only")

    # Clamp to valid range
    final_score = max(_MIN_SCORE, min(_MAX_SCORE, raw_score))

    assert _MIN_SCORE <= final_score <= _MAX_SCORE, (
        f"Score out of range: {final_score}"
    )
    assert len(signals) <= _MAX_SIGNALS, f"Too many signals: {len(signals)}"

    return TrustResult(score=final_score, signals=signals)
