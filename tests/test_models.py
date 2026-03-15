"""Tests for SQLAlchemy models — CRUD, relationships, and enum persistence."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from lgs_directory.models.enums import (
    ChannelType,
    CheckType,
    DiscoverySource,
    PresenceStatus,
    StoreStatus,
)
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store
from lgs_directory.models.validation_log import ValidationLog


class TestStoreModel:
    """Tests for the Store model."""

    def test_create_store(self, db_session: Session, sample_store: Store) -> None:
        """A store can be created with valid fields."""
        assert sample_store.id is not None
        assert isinstance(sample_store.id, UUID)
        assert sample_store.name == "Test Game Shop"
        assert sample_store.status == StoreStatus.CANDIDATE

    def test_store_address_jsonb(self, db_session: Session, sample_store: Store) -> None:
        """Address is stored as JSONB and round-trips correctly."""
        fetched = db_session.get(Store, sample_store.id)
        assert fetched is not None
        assert fetched.address["city"] == "Portland"
        assert fetched.address["state"] == "OR"

    def test_update_store_status(self, db_session: Session, sample_store: Store) -> None:
        """Store status can be updated."""
        sample_store.status = StoreStatus.VERIFIED
        db_session.flush()

        fetched = db_session.get(Store, sample_store.id)
        assert fetched is not None
        assert fetched.status == StoreStatus.VERIFIED

    def test_create_store_with_google_place_id(self, db_session: Session) -> None:
        """A store can be created with a google_place_id."""
        store = Store(
            name="Google Found Shop",
            address={
                "street": "456 Oak Ave", "city": "Seattle",
                "state": "WA", "zip_code": "98101",
            },
            google_place_id="ChIJN1t_tDeuEmsRUsoyG83frY4",
            status=StoreStatus.CANDIDATE,
            discovery_source=DiscoverySource.GOOGLE_PLACES,
        )
        db_session.add(store)
        db_session.flush()

        fetched = db_session.get(Store, store.id)
        assert fetched is not None
        assert fetched.google_place_id == "ChIJN1t_tDeuEmsRUsoyG83frY4"

    def test_enum_persistence(self, db_session: Session, sample_store: Store) -> None:
        """Enum values persist as strings and round-trip correctly."""
        assert sample_store.discovery_source == DiscoverySource.MANUAL

        fetched = db_session.get(Store, sample_store.id)
        assert fetched is not None
        assert fetched.discovery_source == "manual"
        assert fetched.discovery_source == DiscoverySource.MANUAL


class TestOnlinePresenceModel:
    """Tests for the OnlinePresence model."""

    def test_create_presence(self, db_session: Session, sample_store: Store) -> None:
        """A presence can be created linked to a store."""
        presence = OnlinePresence(
            store_id=sample_store.id,
            channel_type=ChannelType.WEBSITE,
            url="https://testgameshop.com",
            status=PresenceStatus.ACTIVE,
        )
        db_session.add(presence)
        db_session.flush()

        assert presence.id is not None
        assert isinstance(presence.id, UUID)
        assert presence.store_id == sample_store.id

    def test_store_presences_relationship(
        self, db_session: Session, sample_store: Store
    ) -> None:
        """Store.presences returns linked presences."""
        p1 = OnlinePresence(
            store_id=sample_store.id,
            channel_type=ChannelType.WEBSITE,
            url="https://testgameshop.com",
        )
        p2 = OnlinePresence(
            store_id=sample_store.id,
            channel_type=ChannelType.TCGPLAYER,
            url="https://tcgplayer.com/seller/test",
        )
        db_session.add_all([p1, p2])
        db_session.flush()

        db_session.refresh(sample_store)
        assert len(sample_store.presences) == 2

    def test_presence_sells_singles(self, db_session: Session, sample_store: Store) -> None:
        """sells_mtg_singles can be set and read."""
        presence = OnlinePresence(
            store_id=sample_store.id,
            channel_type=ChannelType.WEBSITE,
            url="https://testgameshop.com",
            sells_mtg_singles=True,
        )
        db_session.add(presence)
        db_session.flush()

        fetched = db_session.get(OnlinePresence, presence.id)
        assert fetched is not None
        assert fetched.sells_mtg_singles is True


class TestValidationLogModel:
    """Tests for the ValidationLog model."""

    def test_create_validation_log(self, db_session: Session, sample_store: Store) -> None:
        """A validation log can be created for a store."""
        log = ValidationLog(
            store_id=sample_store.id,
            check_type=CheckType.HTTP_CHECK,
            result={"status_code": 200, "ok": True},
        )
        db_session.add(log)
        db_session.flush()

        assert log.id is not None
        assert isinstance(log.id, UUID)

    def test_validation_log_jsonb_result(
        self, db_session: Session, sample_store: Store
    ) -> None:
        """Result JSONB round-trips correctly."""
        result_data = {"status_code": 200, "headers": {"content-type": "text/html"}}
        log = ValidationLog(
            store_id=sample_store.id,
            check_type=CheckType.PLATFORM_DETECT,
            result=result_data,
        )
        db_session.add(log)
        db_session.flush()

        fetched = db_session.get(ValidationLog, log.id)
        assert fetched is not None
        assert fetched.result["status_code"] == 200
        assert fetched.result["headers"]["content-type"] == "text/html"

    def test_validation_log_with_presence(
        self, db_session: Session, sample_store: Store
    ) -> None:
        """A validation log can reference a specific presence."""
        presence = OnlinePresence(
            store_id=sample_store.id,
            channel_type=ChannelType.WEBSITE,
            url="https://testgameshop.com",
        )
        db_session.add(presence)
        db_session.flush()

        log = ValidationLog(
            store_id=sample_store.id,
            presence_id=presence.id,
            check_type=CheckType.SINGLES_DETECT,
            result={"detected": True, "confidence": 0.95},
        )
        db_session.add(log)
        db_session.flush()

        assert log.presence_id == presence.id

    def test_store_validation_logs_relationship(
        self, db_session: Session, sample_store: Store
    ) -> None:
        """Store.validation_logs returns linked logs."""
        log = ValidationLog(
            store_id=sample_store.id,
            check_type=CheckType.MANUAL_REVIEW,
            result={"notes": "Looks good"},
        )
        db_session.add(log)
        db_session.flush()

        db_session.refresh(sample_store)
        assert len(sample_store.validation_logs) == 1
        assert sample_store.validation_logs[0].check_type == CheckType.MANUAL_REVIEW
