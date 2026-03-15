"""Alembic environment configuration."""

from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy import create_engine

from alembic import context

from lgs_directory.config import get_settings
from lgs_directory.models import Base  # noqa: F401 — registers all models

# Alembic Config object
config = context.config

# Set up loggers from the .ini file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use our models' metadata for autogenerate
target_metadata = Base.metadata


def _get_url() -> str:
    """Get migration URL: prefer MIGRATION_DATABASE_URL, fall back to DATABASE_URL."""
    settings = get_settings()
    url = settings.migration_database_url or settings.database_url
    assert url, "DATABASE_URL or MIGRATION_DATABASE_URL must be set"
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emit SQL without a live connection."""
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with a live database connection."""
    connectable = create_engine(_get_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
