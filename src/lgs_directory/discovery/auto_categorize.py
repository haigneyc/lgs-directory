"""Auto-categorize stores based on their website content products."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from lgs_directory.discovery.categories import assign_categories
from lgs_directory.models.store_external_ref import StoreExternalRef

logger = logging.getLogger(__name__)

# Maps product tags (from website_content payload) to store categories.
# Keys are normalized product identifiers stored in the payload "products" array.
_PRODUCT_TO_CATEGORY: dict[str, str] = {
    "mtg": "lgs",
    "pokemon": "lgs",
    "yugioh": "lgs",
    "fab": "lgs",
    "board_games": "lgs",
    "dnd": "lgs",
    "miniatures": "hobby_miniatures",
    "warhammer": "hobby_miniatures",
    "games workshop": "hobby_miniatures",
    "comics": "comic_shop",
    "comic": "comic_shop",
    "retro": "retro_games",
    "vintage": "retro_games",
    "classic games": "retro_games",
}

# Safety bounds
_MAX_STORES = 50_000
_MAX_PRODUCTS_PER_STORE = 100


def auto_categorize_from_content(session: Session) -> tuple[int, int]:
    """Scan website_content refs and assign categories based on product tags.

    Returns (stores_processed, categories_assigned).
    """
    assert session is not None, "session must not be None"

    stmt = (
        select(StoreExternalRef)
        .where(StoreExternalRef.provider == "website_content")
        .where(StoreExternalRef.payload.isnot(None))
        .limit(_MAX_STORES)
    )
    refs = list(session.execute(stmt).scalars().all())
    assert isinstance(refs, list), "refs must be a list"

    stores_processed = 0
    categories_assigned = 0

    bound = min(len(refs), _MAX_STORES)
    for i in range(bound):
        ref = refs[i]
        payload = ref.payload
        if payload is None:
            continue

        products = payload.get("products", [])
        if not isinstance(products, list):
            continue

        # Determine categories from products
        cats_to_assign: set[str] = set()
        product_bound = min(len(products), _MAX_PRODUCTS_PER_STORE)
        for j in range(product_bound):
            product = products[j]
            if not isinstance(product, str):
                continue
            cat = _PRODUCT_TO_CATEGORY.get(product)
            if cat is not None:
                cats_to_assign.add(cat)

        if len(cats_to_assign) > 0:
            store_id = ref.store_id
            assert isinstance(store_id, UUID), "store_id must be a UUID"
            added = assign_categories(
                store_id,
                list(cats_to_assign),
                session,
            )
            categories_assigned += added
            stores_processed += 1

    assert stores_processed >= 0, "stores_processed must be non-negative"
    assert categories_assigned >= 0, "categories_assigned must be non-negative"

    logger.info(
        "Auto-categorized %d stores, assigned %d new categories",
        stores_processed,
        categories_assigned,
    )
    return stores_processed, categories_assigned
