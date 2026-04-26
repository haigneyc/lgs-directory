"""Quality filters for the ingestion pipeline — reject obvious non-game stores.

Provides name-based blocklist filtering, Google Places type filtering,
content scraper confidence gating, and a 3-tier classifier used by the
OSM-state discovery pipeline.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import StrEnum

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
    # --- Big retail chains ---
    re.compile(r"\bbarnes\s+&?\s*noble\b", re.IGNORECASE),
    re.compile(r"\bbest\s+buy\b", re.IGNORECASE),
    re.compile(r"\bhobby\s+lobby\b", re.IGNORECASE),
    re.compile(r"\btarget\b", re.IGNORECASE),
    re.compile(r"\bh-e-b\b", re.IGNORECASE),
    re.compile(r"\btractor\s+supply\b", re.IGNORECASE),
    re.compile(r"\bbuild-a-bear\b", re.IGNORECASE),
    re.compile(r"\bwalmart\b", re.IGNORECASE),
    re.compile(r"\bdollar\s+general\b", re.IGNORECASE),
    re.compile(r"\bdollar\s+tree\b", re.IGNORECASE),
    re.compile(r"\bfamily\s+dollar\b", re.IGNORECASE),
    re.compile(r"\bfive\s+below\b", re.IGNORECASE),
    re.compile(r"\bmarshalls\b", re.IGNORECASE),
    re.compile(r"\btj\s*maxx\b", re.IGNORECASE),
    re.compile(r"\bross\b", re.IGNORECASE),
    re.compile(r"\bhomegoods\b", re.IGNORECASE),
    re.compile(r"\bbed\s+bath\b", re.IGNORECASE),
    re.compile(r"\blids\b", re.IGNORECASE),
    re.compile(r"\bdgx\b", re.IGNORECASE),
    re.compile(r"\bwalgreens\b", re.IGNORECASE),
    re.compile(r"\bcvs\b", re.IGNORECASE),
    re.compile(r"\bmichaels\b", re.IGNORECASE),
    # --- False positive business types ---
    re.compile(r"\barmory\b", re.IGNORECASE),
    re.compile(r"\barmoury\b", re.IGNORECASE),
    re.compile(r"\bgun\b", re.IGNORECASE),
    re.compile(r"\bfirearm\b", re.IGNORECASE),
    re.compile(r"\bembroidery\b", re.IGNORECASE),
    re.compile(r"\bfitness\b", re.IGNORECASE),
    re.compile(r"\bgym\b", re.IGNORECASE),
    re.compile(r"\bhemp\b", re.IGNORECASE),
    re.compile(r"\bcookie\b", re.IGNORECASE),
    re.compile(r"\bbakery\b", re.IGNORECASE),
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


# ---------------------------------------------------------------------------
# Chain game-store blocklist (mirror of LFS is_chain_pet_store shape)
# ---------------------------------------------------------------------------
#
# Big-box and chain retailers that occasionally get tagged ``shop=games``
# or ``shop=video_games`` on OSM. They drown out the per-state signal,
# never qualify as a true LGS, and are already covered (or explicitly
# excluded) by the Google-seeded path.
_CHAIN_GAME_STORE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bgamestop\b", re.IGNORECASE),
    re.compile(r"\bbest\s+buy\b", re.IGNORECASE),
    re.compile(r"\bwalmart\b", re.IGNORECASE),
    re.compile(r"\btarget\b", re.IGNORECASE),
    re.compile(r"\bbarnes\s+&?\s*noble\b", re.IGNORECASE),
    re.compile(r"\bbooks[\s-]*a[\s-]*million\b", re.IGNORECASE),
    re.compile(r"\bb&n\b", re.IGNORECASE),
    re.compile(r"\bmicrocenter\b", re.IGNORECASE),
    re.compile(r"\bmicro\s+center\b", re.IGNORECASE),
    re.compile(r"\bhot\s+topic\b", re.IGNORECASE),
    re.compile(r"\bspirit\s+halloween\b", re.IGNORECASE),
    re.compile(r"\bparty\s+city\b", re.IGNORECASE),
    re.compile(r"\bhobby\s+lobby\b", re.IGNORECASE),
    re.compile(r"\bmichaels\b", re.IGNORECASE),
    re.compile(r"\bdollar\s+(store|tree|general)\b", re.IGNORECASE),
    re.compile(r"\bfamily\s+dollar\b", re.IGNORECASE),
    re.compile(r"\bfive\s+below\b", re.IGNORECASE),
    re.compile(r"\bcostco\b", re.IGNORECASE),
    re.compile(r"\bsam'?s\s+club\b", re.IGNORECASE),
    re.compile(r"\bbjs?\s+wholesale\b", re.IGNORECASE),
    re.compile(r"\btoys\s*r\s*us\b", re.IGNORECASE),
    re.compile(r"\bbuild[\s-]*a[\s-]*bear\b", re.IGNORECASE),
]


def is_chain_game_store(name: str) -> bool:
    """Return True if the OSM-discovered name is a chain retailer.

    Mirrors ``lfs_locator.discovery.quality_filters.is_chain_pet_store``.
    """
    assert isinstance(name, str), "name must be a string"
    assert len(name) > 0, "name must not be empty"

    for idx, pattern in enumerate(_CHAIN_GAME_STORE_PATTERNS):
        if idx >= _MAX_BLOCKLIST_TERMS:
            break
        if pattern.search(name):
            logger.debug(
                "Chain game store detected by pattern '%s': %s",
                pattern.pattern,
                name,
            )
            return True

    return False


# ---------------------------------------------------------------------------
# 3-tier OSM classifier
# ---------------------------------------------------------------------------
#
# Maps a (name, OSM shop tag) pair to one of three buckets:
#
#   AUTO_ACCEPT     -- strong LGS signal; insert as a normal CANDIDATE.
#   CANDIDATE_QUEUE -- ambiguous; insert as PENDING_REVIEW so the public
#                      site does not see it until a content scrape
#                      promotes it.
#   AUTO_REJECT     -- chain blocklist or non-LGS keyword (salon, vape,
#                      thrift, ...); do not insert.
#
# Verbatim regex from the spec at Outbox/2026-04-25/soren-osm-lgs-spec.md
# §1.2. Don't tune without a measurement first; precision/recall numbers
# are baselined against this exact pattern.
_NAME_REGEX_PATTERN = (
    r"(?i)\b(warhammer|wargames?|wargaming|miniatures?|kitbash|citadel|"
    r"mtg|magic[\s-]?the[\s-]?gathering|pokemon|pok\xe9mon|tcg|"
    r"trading\s*cards?|yu[\s-]?gi[\s-]?oh|flesh\s*and\s*blood|lorcana|"
    r"riftbound|star\s*wars\s*unlimited|board\s*games?|card\s*shop|"
    r"game\s*shop|hobby\s*shop|comic\s*shop|game\s*store|hobby\s*store|"
    r"comic\s*store)\b"
)
_NAME_REGEX: re.Pattern[str] = re.compile(_NAME_REGEX_PATTERN)

# Strong-signal OSM shop tags — AUTO_ACCEPT on the tag alone.
_STRONG_SHOP_TAGS: frozenset[str] = frozenset(
    ["games", "anime", "collector", "comics"]
)

# Medium-signal OSM shop tags — need a name regex hit to AUTO_ACCEPT,
# else CANDIDATE_QUEUE. The regex is the only way to distinguish a
# Warhammer hobby shop from a yarn/model-train hobby shop, or a real
# retro game store from GameStop.
_MEDIUM_SHOP_TAGS: frozenset[str] = frozenset(
    ["hobby", "video_games", "toys", "model"]
)

# Per the spec, drop these tags entirely if they slip through the query:
# arcades, electronics, video rental. They are out of scope for v1.
_OUT_OF_SCOPE_SHOP_TAGS: frozenset[str] = frozenset(
    ["video", "electronics"]
)

# Non-LGS keywords that always force AUTO_REJECT regardless of tag/name
# regex. Mirrors the spec §6.1 explicit reject list.
_NON_LGS_KEYWORD_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bsalon\b", re.IGNORECASE),
    re.compile(r"\btattoo\b", re.IGNORECASE),
    re.compile(r"\bvape\b", re.IGNORECASE),
    re.compile(r"\bsmoke\s+shop\b", re.IGNORECASE),
    re.compile(r"\bdispensary\b", re.IGNORECASE),
    re.compile(r"\bthrift\b", re.IGNORECASE),
    re.compile(r"\bpawn\b", re.IGNORECASE),
    re.compile(r"\bauto\s+repair\b", re.IGNORECASE),
    re.compile(r"\bnail\s+salon\b", re.IGNORECASE),
    re.compile(r"\bbarber\b", re.IGNORECASE),
    re.compile(r"\bdental\b", re.IGNORECASE),
    re.compile(r"\bdentist\b", re.IGNORECASE),
    re.compile(r"\bveterinar", re.IGNORECASE),
    re.compile(r"\bliquor\b", re.IGNORECASE),
    re.compile(r"\bgrocery\b", re.IGNORECASE),
    re.compile(r"\bcar\s+wash\b", re.IGNORECASE),
    re.compile(r"\blaundromat\b", re.IGNORECASE),
]


class FilterTier(StrEnum):
    """Classification tier for an OSM discovery candidate."""

    AUTO_ACCEPT = "auto_accept"
    CANDIDATE_QUEUE = "candidate_queue"
    AUTO_REJECT = "auto_reject"


@dataclass(frozen=True)
class TierClassification:
    """Classification result — tier plus a human-readable reason."""

    tier: FilterTier
    reason: str
    matched_pattern: str | None = None


def _has_lgs_name_signal(name: str) -> bool:
    """Return True if the name matches the LGS keyword regex."""
    assert isinstance(name, str), "name must be a string"
    assert len(name) > 0, "name must not be empty"
    return _NAME_REGEX.search(name) is not None


def _has_non_lgs_keyword(name: str) -> re.Pattern[str] | None:
    """Return the first non-LGS-keyword pattern that matches, or None."""
    assert isinstance(name, str), "name must be a string"
    assert len(name) > 0, "name must not be empty"

    for idx, pattern in enumerate(_NON_LGS_KEYWORD_PATTERNS):
        if idx >= _MAX_BLOCKLIST_TERMS:
            break
        if pattern.search(name):
            return pattern
    return None


def classify_osm_candidate(
    tags: dict[str, str | None],
    name: str,
) -> TierClassification:
    """Classify an OSM candidate into AUTO_ACCEPT / CANDIDATE_QUEUE / AUTO_REJECT.

    Precedence (highest wins):
      1. AUTO_REJECT  -- chain retailer (GameStop, Walmart, ...).
      2. AUTO_REJECT  -- explicit non-LGS keyword in name (salon, vape, ...).
      3. AUTO_REJECT  -- shop tag is in the out-of-scope set.
      4. AUTO_ACCEPT  -- strong-signal shop tag (shop=games / comics /
                          anime / collector).
      5. AUTO_ACCEPT  -- medium-signal shop tag PLUS a name-regex hit
                          (e.g. ``shop=hobby`` + "Warhammer").
      6. CANDIDATE_QUEUE -- medium-signal shop tag, no name-regex hit.
      7. AUTO_REJECT  -- no shop tag at all (defensive default — query
                          should never produce these).

    Args:
        tags: OSM tag dict with at least optional "shop" / "amenity" keys.
        name: Store name (non-empty).
    """
    assert isinstance(tags, dict), "tags must be a dict"
    assert isinstance(name, str), "name must be a string"
    assert len(name) > 0, "name must not be empty"

    # Rule 1: chain blocklist
    if is_chain_game_store(name):
        return TierClassification(
            tier=FilterTier.AUTO_REJECT,
            reason="chain game store blocklist match",
            matched_pattern="chain_blocklist",
        )

    # Rule 2: non-LGS keyword in name
    non_lgs = _has_non_lgs_keyword(name)
    if non_lgs is not None:
        return TierClassification(
            tier=FilterTier.AUTO_REJECT,
            reason=f"non-LGS keyword in name: /{non_lgs.pattern}/",
            matched_pattern=non_lgs.pattern,
        )

    # Determine the active shop tag. OSM allows "shop=hobby;games"
    # (semicolon-separated multi-values); split and take the first known
    # bucket so a multi-tagged node lands in its strongest category.
    raw_tag = (tags.get("shop") or "").strip().lower()
    tag_tokens = [t.strip() for t in raw_tag.split(";") if t.strip()]

    # Rule 3: out-of-scope tag (and no other recognized tag rescuing it)
    has_recognized_tag = any(
        token in _STRONG_SHOP_TAGS or token in _MEDIUM_SHOP_TAGS
        for token in tag_tokens
    )
    if not has_recognized_tag:
        for idx, token in enumerate(tag_tokens):
            if idx >= _MAX_BLOCKLIST_TERMS:
                break
            if token in _OUT_OF_SCOPE_SHOP_TAGS:
                return TierClassification(
                    tier=FilterTier.AUTO_REJECT,
                    reason=f"out-of-scope shop tag: shop={token}",
                    matched_pattern=f"shop={token}",
                )

    # Rule 4: strong-signal tag wins outright
    for idx, token in enumerate(tag_tokens):
        if idx >= _MAX_BLOCKLIST_TERMS:
            break
        if token in _STRONG_SHOP_TAGS:
            return TierClassification(
                tier=FilterTier.AUTO_ACCEPT,
                reason=f"strong-signal OSM tag: shop={token}",
                matched_pattern=f"shop={token}",
            )

    # Rule 5/6: medium-signal tag + name regex disambiguation
    for idx, token in enumerate(tag_tokens):
        if idx >= _MAX_BLOCKLIST_TERMS:
            break
        if token in _MEDIUM_SHOP_TAGS:
            if _has_lgs_name_signal(name):
                return TierClassification(
                    tier=FilterTier.AUTO_ACCEPT,
                    reason=f"medium-signal tag shop={token} + LGS name keyword",
                    matched_pattern=f"shop={token}+name_regex",
                )
            return TierClassification(
                tier=FilterTier.CANDIDATE_QUEUE,
                reason=f"medium-signal tag shop={token}, no LGS name keyword",
                matched_pattern=f"shop={token}",
            )

    # Rule 7: defensive default — should be unreachable from the
    # production query, which only requests known tag values.
    return TierClassification(
        tier=FilterTier.AUTO_REJECT,
        reason="no recognized OSM shop tag",
        matched_pattern=None,
    )


@dataclass
class TierCounts:
    """Per-tier counters for a single ingest run."""

    auto_accept: int = 0
    candidate_queue: int = 0
    auto_reject: int = 0

    def record(self, tier: FilterTier) -> None:
        """Increment the bucket for ``tier``."""
        assert isinstance(tier, FilterTier), "tier must be a FilterTier"

        if tier == FilterTier.AUTO_ACCEPT:
            self.auto_accept += 1
        elif tier == FilterTier.CANDIDATE_QUEUE:
            self.candidate_queue += 1
        else:
            assert tier == FilterTier.AUTO_REJECT
            self.auto_reject += 1

    @property
    def total(self) -> int:
        """Total candidates classified."""
        return self.auto_accept + self.candidate_queue + self.auto_reject

    def __str__(self) -> str:
        total = self.total
        if total == 0:
            return "Tier counts: 0 records"
        return (
            f"Tier counts (of {total}): "
            f"auto_accept={self.auto_accept} "
            f"({self.auto_accept * 100 / total:.1f}%), "
            f"candidate_queue={self.candidate_queue} "
            f"({self.candidate_queue * 100 / total:.1f}%), "
            f"auto_reject={self.auto_reject} "
            f"({self.auto_reject * 100 / total:.1f}%)"
        )
