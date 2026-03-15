"""Store model — represents a physical local game store."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lgs_directory.models.base import Base
from lgs_directory.models.enums import DiscoverySource, StoreStatus, WpnLevel

if TYPE_CHECKING:
    from lgs_directory.models.online_presence import OnlinePresence
    from lgs_directory.models.validation_log import ValidationLog


class Store(Base):
    """A physical local game store in the US."""

    __tablename__ = "stores"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[dict] = mapped_column(JSONB, nullable=False)  # type: ignore[type-arg]
    latitude: Mapped[float | None] = mapped_column(default=None)
    longitude: Mapped[float | None] = mapped_column(default=None)
    phone: Mapped[str | None] = mapped_column(String(30), default=None)
    wpn_id: Mapped[str | None] = mapped_column(String(100), default=None)
    wpn_level: Mapped[WpnLevel | None] = mapped_column(String(20), default=None)
    google_place_id: Mapped[str | None] = mapped_column(String(100), default=None)
    status: Mapped[StoreStatus] = mapped_column(
        String(20),
        default=StoreStatus.CANDIDATE,
    )
    discovery_source: Mapped[DiscoverySource] = mapped_column(
        String(20),
        default=DiscoverySource.MANUAL,
    )
    first_seen: Mapped[datetime] = mapped_column(server_default=text("now()"))
    last_validated: Mapped[datetime | None] = mapped_column(default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    # Relationships
    presences: Mapped[list[OnlinePresence]] = relationship(
        back_populates="store",
        cascade="all, delete-orphan",
    )
    validation_logs: Mapped[list[ValidationLog]] = relationship(
        back_populates="store",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_stores_name", "name"),
        Index("ix_stores_status", "status"),
        Index("ix_stores_address_state_city", text("(address->>'state'), (address->>'city')")),
        Index("ix_stores_google_place_id", "google_place_id"),
    )

    def __repr__(self) -> str:
        return f"<Store(id={self.id!r}, name={self.name!r}, status={self.status!r})>"
