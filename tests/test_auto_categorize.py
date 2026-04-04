"""Tests for auto-categorization from website content."""

from lgs_directory.discovery.auto_categorize import _PRODUCT_TO_CATEGORY


def test_mtg_maps_to_lgs() -> None:
    """MTG product tag should map to lgs category."""
    assert _PRODUCT_TO_CATEGORY["mtg"] == "lgs"
    assert isinstance(_PRODUCT_TO_CATEGORY["mtg"], str)


def test_comics_maps_to_comic_shop() -> None:
    """Comics product tag should map to comic_shop category."""
    assert _PRODUCT_TO_CATEGORY["comics"] == "comic_shop"
    assert isinstance(_PRODUCT_TO_CATEGORY["comics"], str)


def test_comic_singular_maps_to_comic_shop() -> None:
    """Singular 'comic' tag should also map to comic_shop."""
    assert _PRODUCT_TO_CATEGORY["comic"] == "comic_shop"
    assert isinstance(_PRODUCT_TO_CATEGORY["comic"], str)


def test_miniatures_maps_to_hobby() -> None:
    """Miniatures product tag should map to hobby_miniatures."""
    assert _PRODUCT_TO_CATEGORY["miniatures"] == "hobby_miniatures"
    assert isinstance(_PRODUCT_TO_CATEGORY["miniatures"], str)


def test_warhammer_maps_to_hobby() -> None:
    """Warhammer product tag should map to hobby_miniatures."""
    assert _PRODUCT_TO_CATEGORY["warhammer"] == "hobby_miniatures"
    assert isinstance(_PRODUCT_TO_CATEGORY["warhammer"], str)


def test_retro_maps_to_retro_games() -> None:
    """Retro product tag should map to retro_games."""
    assert _PRODUCT_TO_CATEGORY["retro"] == "retro_games"
    assert isinstance(_PRODUCT_TO_CATEGORY["retro"], str)


def test_vintage_maps_to_retro_games() -> None:
    """Vintage product tag should map to retro_games."""
    assert _PRODUCT_TO_CATEGORY["vintage"] == "retro_games"
    assert isinstance(_PRODUCT_TO_CATEGORY["vintage"], str)


def test_all_products_mapped() -> None:
    """Every entry in _PRODUCT_TO_CATEGORY must have a non-empty value."""
    assert len(_PRODUCT_TO_CATEGORY) > 0
    for product, category in _PRODUCT_TO_CATEGORY.items():
        assert isinstance(product, str) and len(product) > 0
        assert isinstance(category, str) and len(category) > 0


def test_all_categories_are_valid() -> None:
    """All mapped categories must be one of the known StoreCategory values."""
    valid_categories = {"lgs", "comic_shop", "retro_games", "hobby_miniatures"}
    assert len(valid_categories) > 0
    for category in _PRODUCT_TO_CATEGORY.values():
        assert category in valid_categories, f"Unknown category: {category}"
