"""Database engine and session management."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from lgs_directory.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine(url_override: str | None = None) -> Engine:
    """Return a cached SQLAlchemy engine.

    Args:
        url_override: Use this URL instead of settings. Useful for tests.
    """
    global _engine  # noqa: PLW0603

    url = url_override or get_settings().database_url
    assert url, "DATABASE_URL must be set"

    if _engine is None or url_override is not None:
        _engine = create_engine(url, echo=False, pool_pre_ping=True)

    assert _engine is not None
    return _engine


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Return a cached session factory bound to the given engine."""
    global _session_factory  # noqa: PLW0603

    if _session_factory is None or engine is not None:
        resolved_engine = engine or get_engine()
        _session_factory = sessionmaker(bind=resolved_engine, expire_on_commit=False)

    assert _session_factory is not None
    return _session_factory


@contextmanager
def get_session(engine: Engine | None = None) -> Generator[Session, None, None]:
    """Yield a transactional session that commits on success, rolls back on error."""
    factory = get_session_factory(engine)
    session = factory()
    assert session is not None

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_globals() -> None:
    """Reset cached engine and session factory. Used in tests."""
    global _engine, _session_factory  # noqa: PLW0603
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
