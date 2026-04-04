"""Tests for cross-source deduplication via store_external_refs."""

from __future__ import annotations

from sqlalchemy.orm import Session

from lgs_directory.discovery.dedup import (
    find_by_external_ref,
    upsert_external_ref,
)
from lgs_directory.models.store import Store
from lgs_directory.models.store_external_ref import StoreExternalRef


class TestFindByExternalRef:
    """Tests for find_by_external_ref()."""

    def test_returns_none_when_no_ref_exists(self, db_session: Session) -> None:
        result = find_by_external_ref("games_workshop", "gw-999", db_session)
        assert result is None

    def test_finds_store_by_external_ref(
        self, db_session: Session, sample_store: Store
    ) -> None:
        assert sample_store.id is not None
        ref = StoreExternalRef(
            store_id=sample_store.id,
            provider="games_workshop",
            external_id="gw-123",
        )
        db_session.add(ref)
        db_session.flush()

        result = find_by_external_ref("games_workshop", "gw-123", db_session)
        assert result is not None
        assert result.id == sample_store.id
        assert result.name == sample_store.name

    def test_different_provider_no_match(
        self, db_session: Session, sample_store: Store
    ) -> None:
        assert sample_store.id is not None
        ref = StoreExternalRef(
            store_id=sample_store.id,
            provider="games_workshop",
            external_id="gw-123",
        )
        db_session.add(ref)
        db_session.flush()

        result = find_by_external_ref("league_comic_geeks", "gw-123", db_session)
        assert result is None

    def test_different_external_id_no_match(
        self, db_session: Session, sample_store: Store
    ) -> None:
        assert sample_store.id is not None
        ref = StoreExternalRef(
            store_id=sample_store.id,
            provider="games_workshop",
            external_id="gw-123",
        )
        db_session.add(ref)
        db_session.flush()

        result = find_by_external_ref("games_workshop", "gw-456", db_session)
        assert result is None


class TestUpsertExternalRef:
    """Tests for upsert_external_ref()."""

    def test_creates_new_ref(
        self, db_session: Session, sample_store: Store
    ) -> None:
        assert sample_store.id is not None
        ref = upsert_external_ref(
            sample_store.id, "games_workshop", "gw-123", db_session
        )
        db_session.flush()

        assert isinstance(ref, StoreExternalRef)
        assert ref.provider == "games_workshop"
        assert ref.external_id == "gw-123"
        assert ref.store_id == sample_store.id

    def test_updates_existing_ref(
        self, db_session: Session, sample_store: Store
    ) -> None:
        assert sample_store.id is not None
        # Create initial ref
        ref1 = upsert_external_ref(
            sample_store.id, "games_workshop", "gw-123", db_session
        )
        db_session.flush()
        assert isinstance(ref1, StoreExternalRef)

        # Upsert again -- should update last_seen, not create duplicate
        ref2 = upsert_external_ref(
            sample_store.id, "games_workshop", "gw-123", db_session
        )
        db_session.flush()
        assert isinstance(ref2, StoreExternalRef)
        assert ref2.provider == "games_workshop"

    def test_multiple_providers_same_store(
        self, db_session: Session, sample_store: Store
    ) -> None:
        assert sample_store.id is not None
        ref_gw = upsert_external_ref(
            sample_store.id, "games_workshop", "gw-123", db_session
        )
        ref_comic = upsert_external_ref(
            sample_store.id, "league_comic_geeks", "lcg-456", db_session
        )
        db_session.flush()

        assert ref_gw.provider == "games_workshop"
        assert ref_comic.provider == "league_comic_geeks"

        # Both should resolve to the same store
        found_gw = find_by_external_ref("games_workshop", "gw-123", db_session)
        found_comic = find_by_external_ref("league_comic_geeks", "lcg-456", db_session)
        assert found_gw is not None
        assert found_comic is not None
        assert found_gw.id == found_comic.id
