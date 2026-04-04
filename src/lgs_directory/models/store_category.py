"""StoreCategoryLink model — junction table linking stores to categories."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lgs_directory.models.base import Base
from lgs_directory.models.enums import StoreCategory

if TYPE_CHECKING:
    from lgs_directory.models.store import Store

# Valid category values derived from the StoreCategory enum
_VALID_CATEGORIES = tuple(c.value for c in StoreCategory)


class StoreCategoryLink(Base):
    """Links a store to one or more category tags."""

    __tablename__ = "store_categories"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    store_id: Mapped[UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(30), nullable=False)

    # Bidirectional relationship back to Store
    store: Mapped[Store] = relationship(back_populates="category_links")

    __table_args__ = (
        UniqueConstraint("store_id", "category"),
        CheckConstraint(
            f"category IN ({', '.join(repr(v) for v in _VALID_CATEGORIES)})",
            name="ck_store_categories_valid_category",
        ),
        Index("ix_store_categories_store_id", "store_id"),
        Index("ix_store_categories_category", "category"),
    )

    def __repr__(self) -> str:
        return f"<StoreCategoryLink(store_id={self.store_id!r}, category={self.category!r})>"
