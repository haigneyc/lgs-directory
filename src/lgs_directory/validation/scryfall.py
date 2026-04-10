"""Scryfall API client — market reference prices for probe cards."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

logger = logging.getLogger(__name__)

PROBE_CARDS: list[str] = [
    "Lightning Bolt",
    "Counterspell",
    "Sol Ring",
    "Thoughtseize",
    "Collected Company",
    "Cyclonic Rift",
    "Arid Mesa",
    "Ragavan, Nimble Pilferer",
]

_SCRYFALL_API_URL = "https://api.scryfall.com"
_RATE_LIMIT_SECS = 0.1
_TIMEOUT_SECS = 15
_MAX_PROBE_CARDS = 20  # Upper bound for loop safety

# Module-level cache: card_name -> MarketPrice
_price_cache: dict[str, MarketPrice] = {}


@dataclass(frozen=True)
class MarketPrice:
    """Market reference price for a single card from Scryfall."""

    card_name: str
    set_code: str
    usd_market: float
    usd_low: float
    fetched_at: datetime


def fetch_market_price(card_name: str) -> MarketPrice | None:
    """Fetch market price for a single card via Scryfall fuzzy search.

    Returns parsed MarketPrice or None on failure.
    """
    assert isinstance(card_name, str) and len(card_name) > 0, "card_name must be non-empty"

    # Check cache first
    if card_name in _price_cache:
        return _price_cache[card_name]

    try:
        with httpx.Client(timeout=_TIMEOUT_SECS) as client:
            response = client.get(
                f"{_SCRYFALL_API_URL}/cards/named",
                params={"fuzzy": card_name},
            )
            if response.status_code != 200:
                logger.warning("Scryfall returned %d for %s", response.status_code, card_name)
                return None

            data = response.json()
            assert isinstance(data, dict), "Scryfall response must be a dict"

            prices = data.get("prices", {})
            assert isinstance(prices, dict), "prices must be a dict"

            usd_market_raw = prices.get("usd")
            usd_low_raw = prices.get("usd")  # Scryfall uses "usd" for market
            if usd_market_raw is None:
                logger.warning("No USD price for %s", card_name)
                return None

            result = MarketPrice(
                card_name=data.get("name", card_name),
                set_code=data.get("set", "unknown"),
                usd_market=float(usd_market_raw),
                usd_low=float(usd_low_raw),
                fetched_at=datetime.now(tz=UTC),
            )
            assert isinstance(result.usd_market, float)

            _price_cache[card_name] = result
            return result

    except httpx.HTTPError as exc:
        logger.warning("Scryfall fetch failed for %s: %s", card_name, exc)
        return None
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("Scryfall parse failed for %s: %s", card_name, exc)
        return None


def fetch_probe_prices() -> list[MarketPrice]:
    """Fetch market prices for all probe cards with rate limiting.

    Uses module-level cache so repeated calls within a run are free.
    Returns list of successfully fetched MarketPrice objects.
    """
    assert len(PROBE_CARDS) <= _MAX_PROBE_CARDS, "Probe card list exceeds safety bound"

    results: list[MarketPrice] = []

    for i, card_name in enumerate(PROBE_CARDS):
        assert isinstance(card_name, str)

        # Rate limit between requests (skip if cached)
        if i > 0 and card_name not in _price_cache:
            time.sleep(_RATE_LIMIT_SECS)

        price = fetch_market_price(card_name)
        if price is not None:
            results.append(price)

    logger.info("Fetched %d/%d probe card prices", len(results), len(PROBE_CARDS))
    assert len(results) <= len(PROBE_CARDS)
    return results


def clear_price_cache() -> None:
    """Reset the module-level price cache (for testing)."""
    _price_cache.clear()
    assert len(_price_cache) == 0
