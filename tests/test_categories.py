"""Tests for category assignment utilities."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from lgs_directory.discovery.categories import (
    _VALID_CATEGORY_VALUES,
    assign_categories,
    get_default_categories,
)
from lgs_directory.models.enums import StoreCategory


def test_default_categories_wpn() -> None:
    """WPN discovery should default to lgs."""
    result = get_default_categories("wpn")
    assert result == [StoreCategory.LGS]
    assert isinstance(result, list)


def test_default_categories_games_workshop() -> None:
    """Games Workshop discovery should default to hobby_miniatures."""
    result = get_default_categories("games_workshop")
    assert result == [StoreCategory.HOBBY_MINIATURES]
    assert isinstance(result, list)


def test_default_categories_comicbookstores() -> None:
    """comicbookstores imports should default to comic_shop."""
    result = get_default_categories("comicbookstores")
    assert result == [StoreCategory.COMIC_SHOP]
    assert isinstance(result, list)


def test_default_categories_unknown() -> None:
    """Unknown sources should return empty list."""
    result = get_default_categories("unknown_source")
    assert result == []
    assert isinstance(result, list)


def test_default_categories_comic() -> None:
    """League of Comic Geeks should default to comic_shop."""
    result = get_default_categories("league_comic_geeks")
    assert result == [StoreCategory.COMIC_SHOP]
    assert isinstance(result, list)


def test_default_categories_retro() -> None:
    """Video Game Sage should default to retro_games."""
    result = get_default_categories("video_game_sage")
    assert result == [StoreCategory.RETRO_GAMES]
    assert isinstance(result, list)


class TestAssignCategories:
    """Tests for the assign_categories function with mocked session."""

    def _make_mock_session(self, existing: list[str] | None = None) -> MagicMock:
        """Build a mock SQLAlchemy session that returns existing categories."""
        session = MagicMock()
        existing_cats = existing if existing is not None else []
        session.execute.return_value.scalars.return_value.all.return_value = existing_cats
        return session

    def test_assign_single_category(self) -> None:
        """Assigning a new category returns 1 and calls session.add."""
        session = self._make_mock_session(existing=[])
        store_id = uuid4()

        added = assign_categories(store_id, [StoreCategory.LGS], session)

        assert added == 1
        assert session.add.call_count == 1

    def test_assign_skips_duplicates(self) -> None:
        """Assigning a category that already exists returns 0."""
        session = self._make_mock_session(existing=["lgs"])
        store_id = uuid4()

        added = assign_categories(store_id, [StoreCategory.LGS], session)

        assert added == 0
        assert session.add.call_count == 0

    def test_assign_multiple_categories(self) -> None:
        """Assigning multiple new categories returns the correct count."""
        session = self._make_mock_session(existing=[])
        store_id = uuid4()

        cats = [StoreCategory.LGS, StoreCategory.COMIC_SHOP]
        added = assign_categories(store_id, cats, session)

        assert added == 2
        assert session.add.call_count == 2

    def test_assign_mixed_new_and_existing(self) -> None:
        """Assigning a mix of new and existing categories counts only new ones."""
        session = self._make_mock_session(existing=["lgs"])
        store_id = uuid4()

        cats = [StoreCategory.LGS, StoreCategory.HOBBY_MINIATURES]
        added = assign_categories(store_id, cats, session)

        assert added == 1
        assert session.add.call_count == 1

    def test_assign_rejects_invalid_category(self) -> None:
        """Invalid category values must raise an assertion error."""
        session = self._make_mock_session(existing=[])
        store_id = uuid4()

        with pytest.raises(AssertionError, match="Invalid categories"):
            assign_categories(store_id, ["not_a_real_category"], session)

    def test_assign_rejects_empty_list(self) -> None:
        """Empty categories list must raise an assertion error."""
        session = self._make_mock_session(existing=[])
        store_id = uuid4()

        with pytest.raises(AssertionError):
            assign_categories(store_id, [], session)

    def test_assign_rejects_non_uuid_store_id(self) -> None:
        """Non-UUID store_id must raise an assertion error."""
        session = self._make_mock_session(existing=[])

        with pytest.raises(AssertionError, match="store_id must be a UUID"):
            assign_categories("not-a-uuid", [StoreCategory.LGS], session)  # type: ignore[arg-type]

    def test_valid_category_values_match_enum(self) -> None:
        """The valid category values set matches all StoreCategory members."""
        enum_values = {c.value for c in StoreCategory}
        assert enum_values == _VALID_CATEGORY_VALUES
