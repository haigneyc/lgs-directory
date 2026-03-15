"""Application configuration via pydantic-settings."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        description="PostgreSQL connection string (SQLAlchemy format)",
    )
    migration_database_url: str | None = Field(
        default=None,
        description="Direct PostgreSQL connection for Alembic migrations (bypasses pooler)",
    )
    test_database_url: str | None = Field(
        default=None,
        description="PostgreSQL connection string for tests",
    )
    google_places_api_key: str | None = Field(
        default=None,
        description="Google Places API key for store discovery",
    )
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key for LLM-based validation",
    )
    llm_budget_cents: int = Field(
        default=500,
        description="Maximum LLM spend per validation run in cents",
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached settings instance."""
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = Settings()

    assert _settings is not None
    return _settings
