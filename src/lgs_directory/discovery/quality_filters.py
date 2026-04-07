"""Quality filters for the ingestion pipeline — reject obvious non-game stores.

Provides name-based blocklist filtering, Google Places type filtering,
and content scraper confidence gating.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Upper bound for iteration over blocklist/type sets (safety cap)
_MAX_BLOCKLIST_TERMS = 200
_MAX_GOOGLE_TYPES = 100


# ---------------------------------------------------------------------------
# Name-based blocklist
# ---------------------------------------------------------------------------

# Compiled patterns for non-game-store keywords in store names.
# Each pattern is case-insensitive and word-boundary-aware where practical.
_NAME_BLOCKLIST_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bliquor\b", re.IGNORECASE),
    re.compile(r"\bwine\b", re.IGNORECASE),
    re.compile(r"\bbeer\b", re.IGNORECASE),
    re.compile(r"\bbrewery\b", re.IGNORECASE),
    re.compile(r"\bpharmacy\b", re.IGNORECASE),
    re.compile(r"\bdrugstore\b", re.IGNORECASE),
    re.compile(r"\bgrocery\b", re.IGNORECASE),
    re.compile(r"\bsupermarket\b", re.IGNORECASE),
    re.compile(r"\bgas\s+station\b", re.IGNORECASE),
    re.compile(r"\blaundromat\b", re.IGNORECASE),
    re.compile(r"\bdry\s+clean", re.IGNORECASE),
    re.compile(r"\bnail\s+salon\b", re.IGNORECASE),
    re.compile(r"\bbarber\b", re.IGNORECASE),
    re.compile(r"\bhair\s+salon\b", re.IGNORECASE),
    re.compile(r"\bauto\s+repair\b", re.IGNORECASE),
    re.compile(r"\bcar\s+wash\b", re.IGNORECASE),
    re.compile(r"\bdentist\b", re.IGNORECASE),
    re.compile(r"\bdental\b", re.IGNORECASE),
    re.compile(r"\bmedical\b", re.IGNORECASE),
    re.compile(r"\bveterinar", re.IGNORECASE),
    re.compile(r"\bpet\s+store\b", re.IGNORECASE),
    re.compile(r"\bpet\s+shop\b", re.IGNORECASE),
    re.compile(r"\bconvenience\s+store\b", re.IGNORECASE),
    re.compile(r"\bdollar\s+(store|tree|general)\b", re.IGNORECASE),
    re.compile(r"\btattoo\b", re.IGNORECASE),
    re.compile(r"\bpawn\b", re.IGNORECASE),
    re.compile(r"\bcheck\s+cash", re.IGNORECASE),
    re.compile(r"\btobacco\b", re.IGNORECASE),
    re.compile(r"\bvape\b", re.IGNORECASE),
    re.compile(r"\bsmoke\s+shop\b", re.IGNORECASE),
    re.compile(r"\bcbd\b", re.IGNORECASE),
    re.compile(r"\bdispensary\b", re.IGNORECASE),
    re.compile(r"\bcigar", re.IGNORECASE),
    re.compile(r"\bthrift", re.IGNORECASE),
    re.compile(r"\bantique", re.IGNORECASE),
    re.compile(r"\bice\s+cream\b", re.IGNORECASE),
    re.compile(r"\bsporting\s+goods\b", re.IGNORECASE),
    re.compile(r"\bappliance\b", re.IGNORECASE),
    re.compile(r"\bcrafting\b", re.IGNORECASE),
    re.compile(r"\bphone\s+repair\b", re.IGNORECASE),
    re.compile(r"\bmobile\s+repair\b", re.IGNORECASE),
    re.compile(r"\bdata\s+recovery\b", re.IGNORECASE),
]

# Name patterns that indicate the store IS game/hobby-related,
# used to whitelist stores that might otherwise match a blocklist term
# (e.g., "Beer & Board Games").
_NAME_ALLOWLIST_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bgame", re.IGNORECASE),
    re.compile(r"\bcomic", re.IGNORECASE),
    re.compile(r"\bhobby\b", re.IGNORECASE),
    re.compile(r"\btrading\s*cards?\b", re.IGNORECASE),
    re.compile(r"\bcollectible\s*cards?\b", re.IGNORECASE),
    re.compile(r"\bcard\s*(game|shop|store)\b", re.IGNORECASE),
    re.compile(r"\btcg\b", re.IGNORECASE),
    re.compile(r"\btabletop\b", re.IGNORECASE),
    re.compile(r"\bminiature", re.IGNORECASE),
    re.compile(r"\bwarhammer\b", re.IGNORECASE),
    re.compile(r"\bpok[eé]mon\b", re.IGNORECASE),
    re.compile(r"\bmtg\b", re.IGNORECASE),
    re.compile(r"\bd&d\b", re.IGNORECASE),
    re.compile(r"\brpg\b", re.IGNORECASE),
    re.compile(r"\bboard\s+game", re.IGNORECASE),
    re.compile(r"\bretro\s+(game|gaming|video|arcade)\b", re.IGNORECASE),
]


def is_name_blocked(name: str) -> bool:
    """Check if a store name matches the non-game blocklist.

    Returns True if the name contains a blocklisted term
    AND does not contain a game-related allowlist term.
    """
    assert isinstance(name, str), "name must be a string"
    assert len(name) > 0, "name must not be empty"

    # First, check if any allowlist term is present
    for idx, pattern in enumerate(_NAME_ALLOWLIST_PATTERNS):
        if idx >= _MAX_BLOCKLIST_TERMS:
            break
        if pattern.search(name):
            return False  # Allowlisted — do not block

    # Then, check blocklist
    for idx, pattern in enumerate(_NAME_BLOCKLIST_PATTERNS):
        if idx >= _MAX_BLOCKLIST_TERMS:
            break
        if pattern.search(name):
            logger.debug("Name blocked by pattern '%s': %s", pattern.pattern, name)
            return True

    return False


# ---------------------------------------------------------------------------
# Google Places types filtering
# ---------------------------------------------------------------------------

# Google types that indicate a non-game business
_BLOCKED_GOOGLE_TYPES: frozenset[str] = frozenset([
    "liquor_store",
    "grocery_store",
    "pharmacy",
    "gas_station",
    "laundromat",
    "beauty_salon",
    "hair_care",
    "dentist",
    "veterinary_care",
    "car_repair",
    "car_wash",
    "convenience_store",
    "supermarket",
    "doctor",
    "hospital",
    "bar",
    "night_club",
    "florist",
    "funeral_home",
    "insurance_agency",
    "real_estate_agency",
    "travel_agency",
    "bank",
    "atm",
    "post_office",
    "laundry",
    "locksmith",
    "moving_company",
    "painter",
    "plumber",
    "roofing_contractor",
    "electrician",
    "pet_store",
])

def are_google_types_blocked(types: list[str]) -> bool:
    """Check if Google Places types indicate a non-game business.

    Returns True if the types include a blocked type AND do not include
    any game-relevant type (beyond generic 'store'/'establishment').
    """
    assert isinstance(types, list), "types must be a list"

    if len(types) == 0:
        return False  # No type info — don't block, let other filters decide

    types_set = frozenset(types[:_MAX_GOOGLE_TYPES])

    has_blocked = len(types_set & _BLOCKED_GOOGLE_TYPES) > 0
    if not has_blocked:
        return False

    # Check for game-relevant types that override the block.
    # "book_store" and "toy_store" are strong signals — always override.
    # A generic "store" type alongside a blocked type (e.g., "bar" + "store")
    # also overrides, since it signals a retail business that may be a game store
    # with a secondary function (taproom, cafe, etc.).
    override_types = types_set & {"book_store", "toy_store", "store"}
    return len(override_types) == 0


# ---------------------------------------------------------------------------
# Content scraper confidence gate
# ---------------------------------------------------------------------------

# Threshold: 0 products AND confidence below this = flag/reject
_LOW_CONFIDENCE_THRESHOLD = 0.5


@dataclass(frozen=True)
class ContentGateResult:
    """Result of checking content scraper data for quality."""

    should_reject: bool
    reason: str


def check_content_confidence(
    products: list[str],
    confidence: float,
) -> ContentGateResult:
    """Check whether content scraper results indicate a false positive.

    A store is flagged when the scraper found 0 game products and
    confidence is below the threshold.

    Args:
        products: List of detected product category keys.
        confidence: Scraper confidence score (0.0 - 1.0).

    Returns:
        ContentGateResult indicating whether to reject.
    """
    assert isinstance(products, list), "products must be a list"
    assert isinstance(confidence, float), "confidence must be a float"
    assert 0.0 <= confidence <= 1.0, f"confidence must be 0.0-1.0, got {confidence}"

    if len(products) == 0 and confidence < _LOW_CONFIDENCE_THRESHOLD:
        return ContentGateResult(
            should_reject=True,
            reason=f"0 products detected, confidence={confidence:.2f} "
            f"(threshold={_LOW_CONFIDENCE_THRESHOLD})",
        )

    return ContentGateResult(should_reject=False, reason="")
