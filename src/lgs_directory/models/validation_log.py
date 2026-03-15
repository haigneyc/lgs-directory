"""ValidationLog model — audit trail for validation checks."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lgs_directory.models.base import Base
from lgs_directory.models.enums import CheckType

if TYPE_CHECKING:
    from lgs_directory.models.online_presence import OnlinePresence
    from lgs_directory.models.store import Store


class ValidationLog(Base):
    """A record of a validation check performed on a store or presence."""

    __tablename__ = "validation_logs"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    store_id: Mapped[UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
    )
    presence_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("online_presences.id", ondelete="CASCADE"),
        default=None,
    )
    check_type: Mapped[CheckType] = mapped_column(String(30))
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)  # type: ignore[type-arg]
    timestamp: Mapped[datetime] = mapped_column(server_default=text("now()"))

    # Relationships
    store: Mapped[Store] = relationship(back_populates="validation_logs")
    presence: Mapped[OnlinePresence | None] = relationship(
        back_populates="validation_logs",
    )

    __table_args__ = (
        Index("ix_validation_logs_store_id", "store_id"),
        Index("ix_validation_logs_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<ValidationLog(id={self.id!r}, check={self.check_type!r}, "
            f"store_id={self.store_id!r})>"
        )
