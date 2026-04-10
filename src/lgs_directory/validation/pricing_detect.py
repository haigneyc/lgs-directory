"""Pricing detection orchestrator — freshness + card pricing pipeline."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from lgs_directory.db import get_session, get_session_factory
from lgs_directory.models.enums import (
    ChannelType,
    CheckType,
    Platform,
    PresenceStatus,
    PricingMethod,
    StoreStatus,
)
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store
from lgs_directory.models.validation_log import ValidationLog
from lgs_directory.validation.freshness_detect import FreshnessResult, detect_freshness
from lgs_directory.validation.pricing_search import CardSearchResult, search_card_on_store
from lgs_directory.validation.scryfall import MarketPrice, fetch_probe_prices

logger = logging.getLogger(__name__)

_MAX_PRESENCES = 1000  # Upper bound for loop safety
_MIN_CARDS_FOR_INFERENCE = 3
_SYNCED_TIGHT_THRESHOLD = 10.0  # avg_delta_pct
_SYNCED_LOOSE_THRESHOLD = 15.0
_MANUAL_THRESHOLD = 30.0
_RECENT_DAYS = 30  # Freshness threshold for "recent"
_DB_RETRY_ATTEMPTS = 2


@dataclass(frozen=True)
class PriceSample:
    """A single card price comparison between store and market."""

    card_name: str
    store_price: float
    market_price: float
    delta_pct: float


@dataclass(frozen=True)
class PricingResult:
    """Result of pricing detection for a single presence."""

    pricing_method: PricingMethod
    cards_searched: int
    cards_found: int
    avg_delta_pct: float
    price_samples: list[PriceSample]
    freshness: FreshnessResult
    confidence: float


@dataclass
class PricingReport:
    """Summary of a pricing detection run."""

    total_presences: int = 0
    presences_checked: int = 0
    synced: int = 0
    manual: int = 0
    unknown: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"Pricing detection complete: {self.presences_checked}/{self.total_presences} "
            f"presences — {self.synced} synced, {self.manual} manual, "
            f"{self.unknown} unknown, {self.errors} errors"
        )


def _infer_pricing_method(
    avg_delta_pct: float,
    cards_found: int,
    freshness: FreshnessResult,
) -> tuple[PricingMethod, float]:
    """Infer pricing method from average price delta and freshness.

    Returns (PricingMethod, confidence).
    """
    assert isinstance(avg_delta_pct, float) and avg_delta_pct >= 0.0
    assert isinstance(cards_found, int) and cards_found >= 0

    # Insufficient data
    if cards_found < _MIN_CARDS_FOR_INFERENCE:
        return PricingMethod.UNKNOWN, 0.30

    # Check if freshness is recent
    is_recent = False
    if freshness.last_update_detected is not None:
        days_ago = (datetime.now(tz=UTC) - freshness.last_update_detected).days
        is_recent = days_ago <= _RECENT_DAYS

    # Tight sync with recent freshness
    if avg_delta_pct <= _SYNCED_TIGHT_THRESHOLD and is_recent:
        return PricingMethod.SYNCED, 0.85

    # Loose sync
    if avg_delta_pct <= _SYNCED_LOOSE_THRESHOLD:
        return PricingMethod.SYNCED, 0.70

    # High delta — likely manual
    if avg_delta_pct > _MANUAL_THRESHOLD:
        return PricingMethod.MANUAL, 0.80

    # In between — uncertain
    return PricingMethod.UNKNOWN, 0.40


def _coerce_platform(platform: Platform | str | None) -> Platform | None:
    """Normalize platform values loaded from string-backed ORM columns."""
    if platform is None or isinstance(platform, Platform):
        return platform

    if isinstance(platform, str):
        normalized = platform.strip().lower()
        if not normalized:
            return None
        try:
            return Platform(normalized)
        except ValueError:
            logger.warning("Unknown platform value in pricing detection: %s", platform)
            return None

    logger.warning("Unsupported platform type in pricing detection: %r", platform)
    return None


def detect_pricing(
    url: str,
    platform: Platform | str | None,
    market_prices: list[MarketPrice],
) -> PricingResult:
    """Run freshness + pricing detection for one presence.

    Searches for probe cards on the store, compares to market prices,
    and infers the pricing method.

    Returns PricingResult.
    """
    assert isinstance(url, str) and len(url) > 0
    assert isinstance(market_prices, list) and len(market_prices) > 0
    normalized_platform = _coerce_platform(platform)

    # Step 1: Freshness detection
    freshness = detect_freshness(
        url,
        platform=normalized_platform.value if normalized_platform else None,
    )
    assert isinstance(freshness, FreshnessResult)

    # Step 2: Search for probe cards
    search_results: list[CardSearchResult] = []
    for mp in market_prices:
        result = search_card_on_store(url, mp.card_name, normalized_platform)
        search_results.append(result)

    # Step 3: Build price samples
    price_samples: list[PriceSample] = []
    market_by_name = {mp.card_name: mp for mp in market_prices}

    for sr in search_results:
        if not sr.found or sr.store_price is None:
            continue

        mp = market_by_name.get(sr.card_name)
        if mp is None:
            continue

        assert mp.usd_market > 0, "Market price must be positive"
        delta_pct = abs(sr.store_price - mp.usd_market) / mp.usd_market * 100.0

        price_samples.append(PriceSample(
            card_name=sr.card_name,
            store_price=sr.store_price,
            market_price=mp.usd_market,
            delta_pct=round(delta_pct, 1),
        ))

    # Step 4: Compute average delta
    cards_searched = len(market_prices)
    cards_found = len(price_samples)

    if cards_found > 0:
        avg_delta_pct = sum(s.delta_pct for s in price_samples) / cards_found
    else:
        avg_delta_pct = 0.0

    # Step 5: Infer pricing method
    pricing_method, confidence = _infer_pricing_method(avg_delta_pct, cards_found, freshness)

    return PricingResult(
        pricing_method=pricing_method,
        cards_searched=cards_searched,
        cards_found=cards_found,
        avg_delta_pct=round(avg_delta_pct, 1),
        price_samples=price_samples,
        freshness=freshness,
        confidence=confidence,
    )


def detect_and_log_pricing(
    presence: OnlinePresence,
    session: Session,
    market_prices: list[MarketPrice],
) -> PricingResult:
    """Detect pricing for a presence, update ORM fields, and create ValidationLog entries.

    Updates presence.pricing_method and presence.last_price_update_detected.
    Creates FRESHNESS_CHECK and PRICING_CHECK log entries.

    Returns PricingResult.
    """
    assert presence.id is not None, "Presence must be persisted"
    assert presence.url is not None, "Presence must have a URL"
    assert isinstance(market_prices, list)

    logger.info("Detecting pricing for: %s", presence.url)

    result = detect_pricing(presence.url, presence.platform, market_prices)
    now = datetime.now(tz=UTC)

    # Update ORM fields
    presence.pricing_method = result.pricing_method
    presence.last_checked = now

    if result.freshness.last_update_detected is not None:
        presence.last_price_update_detected = result.freshness.last_update_detected

    # Create FRESHNESS_CHECK log
    freshness_data: dict[str, object] = {
        "url": presence.url,
        "method": result.freshness.method,
        "confidence": result.freshness.confidence,
        "signals": result.freshness.freshness_signals,
    }
    if result.freshness.last_update_detected is not None:
        freshness_data["last_update"] = result.freshness.last_update_detected.isoformat()

    freshness_log = ValidationLog(
        store_id=presence.store_id,
        presence_id=presence.id,
        check_type=CheckType.FRESHNESS_CHECK,
        result=freshness_data,
    )
    session.add(freshness_log)

    # Create PRICING_CHECK log
    pricing_data: dict[str, object] = {
        "cards_searched": result.cards_searched,
        "cards_found": result.cards_found,
        "avg_delta_pct": result.avg_delta_pct,
        "pricing_method": result.pricing_method.value,
        "confidence": result.confidence,
        "prices": [
            {
                "card": s.card_name,
                "store_price": s.store_price,
                "market_price": s.market_price,
                "delta_pct": s.delta_pct,
            }
            for s in result.price_samples
        ],
    }

    pricing_log = ValidationLog(
        store_id=presence.store_id,
        presence_id=presence.id,
        check_type=CheckType.PRICING_CHECK,
        result=pricing_data,
    )
    session.add(pricing_log)

    logger.info(
        "  → %s (%.1f%% avg delta, %d/%d cards, conf=%.2f)",
        result.pricing_method.value,
        result.avg_delta_pct,
        result.cards_found,
        result.cards_searched,
        result.confidence,
    )

    assert isinstance(result, PricingResult)
    return result


def _load_pricing_work_items(
    session: Session,
    *,
    limit: int,
) -> list[tuple[UUID, str]]:
    """Return eligible presence IDs and URLs for pricing detection."""
    stmt = (
        select(OnlinePresence.id, OnlinePresence.url)
        .join(Store)
        .where(Store.status == StoreStatus.ACTIVE)
        .where(OnlinePresence.status == PresenceStatus.ACTIVE)
        .where(OnlinePresence.sells_mtg_singles.is_(True))
        .where(OnlinePresence.channel_type == ChannelType.WEBSITE)
        .limit(limit)
    )
    rows = session.execute(stmt).all()
    work_items = [(presence_id, url) for presence_id, url in rows if presence_id is not None]
    assert isinstance(work_items, list)
    return work_items


def _process_presence_with_retry(
    presence_id: UUID,
    presence_url: str,
    session_factory: Callable[[], Session],
    market_prices: list[MarketPrice],
) -> PricingResult:
    """Process one presence in a short transaction, retrying transient DB failures."""
    last_error: OperationalError | None = None

    for attempt in range(1, _DB_RETRY_ATTEMPTS + 1):
        processing_session = session_factory()
        try:
            presence = processing_session.get(OnlinePresence, presence_id)
            if presence is None:
                raise LookupError(f"Presence not found: {presence_id}")

            result = detect_and_log_pricing(presence, processing_session, market_prices)
            processing_session.commit()
            return result
        except OperationalError as exc:
            processing_session.rollback()
            last_error = exc
            logger.warning(
                "DB commit failed for %s on attempt %d/%d: %s",
                presence_url,
                attempt,
                _DB_RETRY_ATTEMPTS,
                exc,
            )
            if attempt == _DB_RETRY_ATTEMPTS:
                raise
        except Exception:
            processing_session.rollback()
            raise
        finally:
            processing_session.close()

    assert last_error is not None
    raise last_error


def run_pricing_detection(
    session: Session | None = None,
    *,
    limit: int = 100,
) -> PricingReport:
    """Run pricing detection on eligible presences.

    Eligible: sells_mtg_singles=True, status=ACTIVE, store.status=ACTIVE.
    Fetches market prices once, then processes presences.

    Returns PricingReport with summary.
    """
    assert 0 < limit <= _MAX_PRESENCES, f"Limit must be 1-{_MAX_PRESENCES}"

    report = PricingReport()

    # Fetch market prices
    logger.info("Fetching probe card market prices...")
    market_prices = fetch_probe_prices()
    if len(market_prices) == 0:
        logger.warning("No market prices fetched — aborting pricing detection")
        return report

    if session is None:
        with get_session() as query_session:
            work_items = _load_pricing_work_items(query_session, limit=limit)
        session_factory = get_session_factory()
    else:
        work_items = _load_pricing_work_items(session, limit=limit)
        session_factory = sessionmaker(bind=session.get_bind(), expire_on_commit=False)

    report.total_presences = len(work_items)
    logger.info("Running pricing detection on %d presences", len(work_items))

    for presence_id, presence_url in work_items:

        try:
            result = _process_presence_with_retry(
                presence_id,
                presence_url,
                session_factory,
                market_prices,
            )
            report.presences_checked += 1

            if result.pricing_method == PricingMethod.SYNCED:
                report.synced += 1
            elif result.pricing_method == PricingMethod.MANUAL:
                report.manual += 1
            else:
                report.unknown += 1

        except Exception as exc:
            logger.warning("Pricing detection failed for %s: %s", presence_url, exc)
            report.errors += 1
            report.error_details.append(f"{presence_url}: {exc}")

    logger.info("%s", report)
    return report
