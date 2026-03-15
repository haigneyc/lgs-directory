"""OnlinePresence model — represents a single online channel for a store."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lgs_directory.models.base import Base
from lgs_directory.models.enums import (
    ChannelType,
    InventorySize,
    Platform,
    PresenceStatus,
    PricingMethod,
)

if TYPE_CHECKING:
    from lgs_directory.models.store import Store
    from lgs_directory.models.validation_log import ValidationLog


class OnlinePresence(Base):
    """An online channel (website, marketplace listing, etc.) for a store."""

    __tablename__ = "online_presences"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    store_id: Mapped[UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
    )
    channel_type: Mapped[ChannelType] = mapped_column(String(20))
    url: Mapped[str] = mapped_column(String(2048))
    platform: Mapped[Platform | None] = mapped_column(String(30), default=None)
    sells_mtg_singles: Mapped[bool | None] = mapped_column(default=None)
    estimated_inventory_size: Mapped[InventorySize | None] = mapped_column(
        String(20),
        default=None,
    )
    pricing_method: Mapped[PricingMethod | None] = mapped_column(
        String(20),
        default=None,
    )
    last_price_update_detected: Mapped[datetime | None] = mapped_column(default=None)
    http_status: Mapped[int | None] = mapped_column(Integer, default=None)
    last_checked: Mapped[datetime | None] = mapped_column(default=None)
    status: Mapped[PresenceStatus] = mapped_column(
        String(20),
        default=PresenceStatus.ACTIVE,
    )

    # Relationships
    store: Mapped[Store] = relationship(back_populates="presences")
    validation_logs: Mapped[list[ValidationLog]] = relationship(
        back_populates="presence",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_online_presences_store_id", "store_id"),
        Index("ix_online_presences_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<OnlinePresence(id={self.id!r}, channel={self.channel_type!r}, "
            f"url={self.url!r})>"
        )
