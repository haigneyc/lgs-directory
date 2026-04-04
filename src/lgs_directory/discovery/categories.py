"""Category assignment utilities for stores discovered from different sources."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from lgs_directory.models.enums import StoreCategory
from lgs_directory.models.store_category import StoreCategoryLink

logger = logging.getLogger(__name__)

# Maps discovery providers to their default category
_PROVIDER_DEFAULT_CATEGORIES: dict[str, list[str]] = {
    "wpn": [StoreCategory.LGS],
    "google_places": [StoreCategory.LGS],
    "games_workshop": [StoreCategory.HOBBY_MINIATURES],
    "comicbookstores": [StoreCategory.COMIC_SHOP],
    "league_comic_geeks": [StoreCategory.COMIC_SHOP],
    "video_game_sage": [StoreCategory.RETRO_GAMES],
}

# Set of valid category values for fast membership checks
_VALID_CATEGORY_VALUES: frozenset[str] = frozenset(c.value for c in StoreCategory)

# Max categories per store (safety bound)
_MAX_CATEGORIES_PER_STORE = 10


def assign_categories(
    store_id: UUID,
    categories: Sequence[str],
    session: Session,
) -> int:
    """Assign one or more categories to a store, skipping duplicates.

    Returns the number of newly assigned categories.
    """
    assert isinstance(store_id, UUID), "store_id must be a UUID"
    assert len(categories) > 0
    assert len(categories) <= _MAX_CATEGORIES_PER_STORE

    # Validate all categories against the StoreCategory enum
    cat_set = set(categories)
    assert all(isinstance(c, str) and len(c) > 0 for c in cat_set), (
        "All categories must be non-empty strings"
    )
    invalid = cat_set - _VALID_CATEGORY_VALUES
    assert len(invalid) == 0, f"Invalid categories: {invalid}"

    # Check existing categories for this store
    existing_stmt = select(StoreCategoryLink.category).where(
        StoreCategoryLink.store_id == store_id
    )
    existing = set(session.execute(existing_stmt).scalars().all())
    assert isinstance(existing, set)

    added = 0
    for cat in categories:
        if cat not in existing:
            link = StoreCategoryLink(store_id=store_id, category=cat)
            session.add(link)
            existing.add(cat)
            added += 1

    return added


def get_default_categories(discovery_source: str) -> list[str]:
    """Return default categories for a given discovery source."""
    assert isinstance(discovery_source, str)
    result = _PROVIDER_DEFAULT_CATEGORIES.get(discovery_source, [])
    assert isinstance(result, list)
    return result
