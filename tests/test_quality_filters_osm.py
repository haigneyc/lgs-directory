"""Tests for the 3-tier OSM classifier in ``quality_filters``."""

from __future__ import annotations

import pytest

from lgs_directory.discovery.quality_filters import (
    FilterTier,
    TierCounts,
    classify_osm_candidate,
    is_chain_game_store,
)

# ---------------------------------------------------------------------------
# Chain blocklist
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "GameStop #4321",
        "Best Buy",
        "Walmart Supercenter",
        "Target",
        "Barnes & Noble",
        "Books-a-Million",
        "Hot Topic",
        "Spirit Halloween",
        "Party City",
        "Hobby Lobby",
        "Dollar Tree",
        "Family Dollar",
        "Costco",
        "Microcenter",
        "Micro Center",
        "Sams Club",
        "BJs Wholesale",
        "Toys R Us",
        "Build-A-Bear",
    ],
)
def test_chain_blocklist_hits(name: str) -> None:
    assert is_chain_game_store(name) is True


@pytest.mark.parametrize(
    "name",
    [
        "Black Knight Wargaming",
        "The Wizard's Chest",
        "Dragons Den TCG",
        "Mile High Comics",
        "Local Hobby & Games",
    ],
)
def test_chain_blocklist_misses(name: str) -> None:
    assert is_chain_game_store(name) is False


# ---------------------------------------------------------------------------
# Strong-signal AUTO_ACCEPT
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("shop_tag", ["games", "comics", "anime", "collector"])
def test_strong_signal_tag_auto_accepts(shop_tag: str) -> None:
    result = classify_osm_candidate(
        tags={"shop": shop_tag},
        name="Some Random Name",
    )
    assert result.tier == FilterTier.AUTO_ACCEPT
    assert f"shop={shop_tag}" in result.reason


def test_multivalue_tag_picks_strong_first() -> None:
    # OSM allows ``shop=hobby;games``; classifier should not be order-dependent.
    result = classify_osm_candidate(
        tags={"shop": "hobby;games"},
        name="Generic Store",
    )
    assert result.tier == FilterTier.AUTO_ACCEPT


# ---------------------------------------------------------------------------
# Medium-signal: name regex disambiguates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("shop_tag", "name"),
    [
        ("hobby", "Black Knight Wargaming"),
        ("hobby", "The Citadel Miniatures Shop"),
        ("video_games", "Retro Game Store of Boulder"),
        ("toys", "Mile High Trading Cards"),
        ("model", "Warhammer Workshop"),
        ("hobby", "MTG and Pokémon Cards"),
        ("hobby", "Yu-Gi-Oh Hobby Shop"),
        ("hobby", "Lorcana Game Store"),
        ("hobby", "Star Wars Unlimited Hobby"),
        ("hobby", "Riftbound Card Shop"),
    ],
)
def test_medium_signal_with_regex_hit_auto_accepts(shop_tag: str, name: str) -> None:
    result = classify_osm_candidate(tags={"shop": shop_tag}, name=name)
    assert result.tier == FilterTier.AUTO_ACCEPT
    assert "name keyword" in result.reason or "LGS name" in result.reason


@pytest.mark.parametrize(
    ("shop_tag", "name"),
    [
        ("hobby", "Knit & Purl"),
        ("hobby", "Crochet Corner"),
        ("toys", "Tiny Tots Boutique"),
        ("video_games", "Joe's Place"),
        ("model", "Train Set World"),
    ],
)
def test_medium_signal_no_regex_routes_to_queue(shop_tag: str, name: str) -> None:
    result = classify_osm_candidate(tags={"shop": shop_tag}, name=name)
    assert result.tier == FilterTier.CANDIDATE_QUEUE


# ---------------------------------------------------------------------------
# AUTO_REJECT precedence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("shop_tag", "name"),
    [
        ("games", "GameStop #1234"),
        ("hobby", "Hobby Lobby"),
        ("video_games", "Best Buy"),
        ("comics", "Walmart Supercenter"),
    ],
)
def test_chain_overrides_strong_tag(shop_tag: str, name: str) -> None:
    result = classify_osm_candidate(tags={"shop": shop_tag}, name=name)
    assert result.tier == FilterTier.AUTO_REJECT
    assert "chain" in result.reason


@pytest.mark.parametrize(
    ("shop_tag", "name"),
    [
        ("games", "Acme Tattoo Parlor"),
        ("hobby", "Vape City"),
        ("toys", "Bob's Smoke Shop"),
        ("collector", "Mountain Dispensary"),
        ("comics", "Old Town Pawn"),
    ],
)
def test_non_lgs_keyword_overrides_tag(shop_tag: str, name: str) -> None:
    result = classify_osm_candidate(tags={"shop": shop_tag}, name=name)
    assert result.tier == FilterTier.AUTO_REJECT


def test_no_recognized_tag_rejects() -> None:
    result = classify_osm_candidate(tags={"shop": "stationery"}, name="Paper Co")
    assert result.tier == FilterTier.AUTO_REJECT


def test_empty_shop_tag_rejects() -> None:
    result = classify_osm_candidate(tags={"shop": None}, name="Whatever Store")
    assert result.tier == FilterTier.AUTO_REJECT


# ---------------------------------------------------------------------------
# TierCounts
# ---------------------------------------------------------------------------


def test_tier_counts_records_each_tier() -> None:
    counts = TierCounts()
    counts.record(FilterTier.AUTO_ACCEPT)
    counts.record(FilterTier.AUTO_ACCEPT)
    counts.record(FilterTier.CANDIDATE_QUEUE)
    counts.record(FilterTier.AUTO_REJECT)
    assert counts.auto_accept == 2
    assert counts.candidate_queue == 1
    assert counts.auto_reject == 1
    assert counts.total == 4
    assert "auto_accept=2" in str(counts)


def test_tier_counts_empty_str() -> None:
    assert "0 records" in str(TierCounts())
