"""StoreExternalRef model — durable external IDs linking stores to external providers."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from lgs_directory.models.base import Base


class StoreExternalRef(Base):
    """Maps a store to an external provider's identifier with optional payload."""

    __tablename__ = "store_external_refs"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    store_id: Mapped[UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, default=None)  # type: ignore[type-arg]
    first_seen: Mapped[datetime] = mapped_column(server_default=text("now()"))
    last_seen: Mapped[datetime] = mapped_column(server_default=text("now()"))

    __table_args__ = (
        UniqueConstraint("provider", "external_id"),
        Index("ix_store_external_refs_store_id", "store_id"),
        Index("ix_store_external_refs_provider", "provider"),
    )

    def __repr__(self) -> str:
        return f"<StoreExternalRef(store_id={self.store_id!r}, provider={self.provider!r}, external_id={self.external_id!r})>"
