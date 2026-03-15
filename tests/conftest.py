"""Test fixtures for the LGS Directory test suite."""

from __future__ import annotations

import os
from collections.abc import Generator
from uuid import UUID

import pytest
from click.testing import CliRunner
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from lgs_directory.models import Base
from lgs_directory.models.enums import ChannelType, DiscoverySource, PresenceStatus, StoreStatus
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store

# Use TEST_DATABASE_URL or fall back to a local PostgreSQL
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/lgs_directory_test",
)


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    """Create the test database engine and tables once per test session."""
    engine = create_engine(TEST_DB_URL, echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """Yield a transactional session that rolls back after each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    session = factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def cli_runner() -> CliRunner:
    """Return a Click CliRunner instance."""
    return CliRunner()


@pytest.fixture()
def sample_store(db_session: Session) -> Store:
    """Insert and return a sample store for testing."""
    store = Store(
        name="Test Game Shop",
        address={
            "street": "123 Main St",
            "city": "Portland",
            "state": "OR",
            "zip_code": "97201",
        },
        phone="503-555-0100",
        status=StoreStatus.CANDIDATE,
        discovery_source=DiscoverySource.MANUAL,
    )
    db_session.add(store)
    db_session.flush()
    assert store.id is not None
    assert isinstance(store.id, UUID)
    return store


@pytest.fixture()
def sample_store_with_presence(db_session: Session, sample_store: Store) -> Store:
    """Insert a store with an active website OnlinePresence."""
    presence = OnlinePresence(
        store_id=sample_store.id,
        channel_type=ChannelType.WEBSITE,
        url="https://testgameshop.com",
        status=PresenceStatus.ACTIVE,
    )
    db_session.add(presence)
    db_session.flush()
    db_session.refresh(sample_store)
    assert len(sample_store.presences) == 1
    assert sample_store.presences[0].url == "https://testgameshop.com"
    return sample_store
