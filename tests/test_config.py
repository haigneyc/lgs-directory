"""Tests for application configuration."""

from __future__ import annotations

import os
from unittest.mock import patch

from lgs_directory.config import Settings


class TestSettings:
    """Tests for Settings config class."""

    def test_picks_up_google_places_key(self) -> None:
        """Settings loads GOOGLE_PLACES_API_KEY from environment."""
        env = {
            "DATABASE_URL": "postgresql+psycopg://test:test@localhost/test",
            "GOOGLE_PLACES_API_KEY": "test-key-123",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

        assert settings.google_places_api_key == "test-key-123"
        assert settings.database_url is not None

    def test_picks_up_anthropic_key(self) -> None:
        """Settings loads ANTHROPIC_API_KEY from environment."""
        env = {
            "DATABASE_URL": "postgresql+psycopg://test:test@localhost/test",
            "ANTHROPIC_API_KEY": "sk-ant-test",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

        assert settings.anthropic_api_key == "sk-ant-test"
        assert settings.database_url is not None

    def test_llm_budget_default(self) -> None:
        """LLM budget defaults to 500 cents."""
        env = {
            "DATABASE_URL": "postgresql+psycopg://test:test@localhost/test",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings(_env_file=None)

        assert settings.llm_budget_cents == 500
        assert settings.google_places_api_key is None

    def test_llm_budget_override(self) -> None:
        """LLM budget can be overridden via environment."""
        env = {
            "DATABASE_URL": "postgresql+psycopg://test:test@localhost/test",
            "LLM_BUDGET_CENTS": "1000",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

        assert settings.llm_budget_cents == 1000
        assert isinstance(settings.llm_budget_cents, int)
