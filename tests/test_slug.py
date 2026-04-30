"""Tests for store slug generation and public slug guard helpers."""

from __future__ import annotations

from lgs_directory.slug import build_store_slug, disambiguate_slug, normalize_state_slug_component


def test_build_store_slug_strips_legal_suffix_and_quotes() -> None:
    """Canonical slug matches the web helper behavior."""
    slug = build_store_slug("Jan's Tropical Games LLC", "Portland", "OR")

    assert slug == "jans-tropical-games-portland-or"


def test_build_store_slug_deduplicates_city_state_suffix() -> None:
    """Names already ending in city/state are not redundantly appended."""
    slug = build_store_slug("Game X Change Gainesville TX", "Gainesville", "TX")

    assert slug == "game-x-change-gainesville-tx"


def test_normalize_state_slug_component_handles_state_names() -> None:
    """Full state names collapse to two-letter slug components."""
    assert normalize_state_slug_component("New York") == "ny"
    assert normalize_state_slug_component("CA") == "ca"


def test_disambiguate_slug_keeps_suffix_when_trimming() -> None:
    """Collision suffix survives max-length trimming."""
    base = "a" * 170
    slug = disambiguate_slug(base, "12345678-1234-4234-9234-123456789abc")

    assert len(slug) == 160
    assert slug.endswith("-123456")
