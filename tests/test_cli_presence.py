"""Tests for the presence CLI commands."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import patch

from click.testing import CliRunner
from sqlalchemy.orm import Session

from lgs_directory.cli.main import cli
from lgs_directory.models.enums import ChannelType, PresenceStatus
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store


@contextmanager
def _patched_session(db_session: Session) -> Generator[Session, None, None]:
    """Context manager that yields the test session without committing."""
    yield db_session


class TestPresenceAdd:
    """Tests for `lgs presence add`."""

    def test_add_presence(
        self, cli_runner: CliRunner, db_session: Session, sample_store: Store
    ) -> None:
        """Adding a presence prints success."""
        with patch(
            "lgs_directory.cli.presence.get_session",
            lambda: _patched_session(db_session),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "presence", "add", str(sample_store.id),
                    "--channel", "website",
                    "--url", "https://testgameshop.com",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "Created presence" in result.output

    def test_add_presence_invalid_store(
        self, cli_runner: CliRunner, db_session: Session
    ) -> None:
        """Adding a presence for a nonexistent store fails."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        with patch(
            "lgs_directory.cli.presence.get_session",
            lambda: _patched_session(db_session),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "presence", "add", fake_id,
                    "--channel", "website",
                    "--url", "https://example.com",
                ],
            )

        assert result.exit_code != 0


class TestPresenceList:
    """Tests for `lgs presence list`."""

    def test_list_empty(
        self, cli_runner: CliRunner, db_session: Session, sample_store: Store
    ) -> None:
        """Listing with no presences shows a message."""
        with patch(
            "lgs_directory.cli.presence.get_session",
            lambda: _patched_session(db_session),
        ):
            result = cli_runner.invoke(
                cli,
                ["presence", "list", str(sample_store.id)],
            )

        assert result.exit_code == 0
        assert "No presences found" in result.output

    def test_list_with_presences(
        self, cli_runner: CliRunner, db_session: Session, sample_store: Store
    ) -> None:
        """Listing shows presences for a store."""
        presence = OnlinePresence(
            store_id=sample_store.id,
            channel_type=ChannelType.WEBSITE,
            url="https://testgameshop.com",
            status=PresenceStatus.ACTIVE,
        )
        db_session.add(presence)
        db_session.flush()

        with patch(
            "lgs_directory.cli.presence.get_session",
            lambda: _patched_session(db_session),
        ):
            result = cli_runner.invoke(
                cli,
                ["presence", "list", str(sample_store.id)],
            )

        assert result.exit_code == 0
        assert "testgameshop.com" in result.output


class TestPresenceEdit:
    """Tests for `lgs presence edit`."""

    def test_edit_presence_url(
        self, cli_runner: CliRunner, db_session: Session, sample_store: Store
    ) -> None:
        """Editing a presence URL updates the record."""
        presence = OnlinePresence(
            store_id=sample_store.id,
            channel_type=ChannelType.WEBSITE,
            url="https://old-url.com",
            status=PresenceStatus.ACTIVE,
        )
        db_session.add(presence)
        db_session.flush()
        assert presence.id is not None

        with patch(
            "lgs_directory.cli.presence.get_session",
            lambda: _patched_session(db_session),
        ):
            result = cli_runner.invoke(
                cli,
                ["presence", "edit", str(presence.id), "--url", "https://new-url.com"],
            )

        assert result.exit_code == 0
        assert "Updated presence" in result.output


class TestPresenceRemove:
    """Tests for `lgs presence remove`."""

    def test_soft_delete(
        self, cli_runner: CliRunner, db_session: Session, sample_store: Store
    ) -> None:
        """Removing without --hard sets status to dead."""
        presence = OnlinePresence(
            store_id=sample_store.id,
            channel_type=ChannelType.WEBSITE,
            url="https://testgameshop.com",
            status=PresenceStatus.ACTIVE,
        )
        db_session.add(presence)
        db_session.flush()
        assert presence.id is not None

        with patch(
            "lgs_directory.cli.presence.get_session",
            lambda: _patched_session(db_session),
        ):
            result = cli_runner.invoke(
                cli,
                ["presence", "remove", str(presence.id)],
            )

        assert result.exit_code == 0
        assert "Soft-deleted" in result.output

        fetched = db_session.get(OnlinePresence, presence.id)
        assert fetched is not None
        assert fetched.status == PresenceStatus.DEAD

    def test_hard_delete(
        self, cli_runner: CliRunner, db_session: Session, sample_store: Store
    ) -> None:
        """Removing with --hard permanently deletes the record."""
        presence = OnlinePresence(
            store_id=sample_store.id,
            channel_type=ChannelType.WEBSITE,
            url="https://testgameshop.com",
            status=PresenceStatus.ACTIVE,
        )
        db_session.add(presence)
        db_session.flush()
        assert presence.id is not None
        pid = presence.id

        with patch(
            "lgs_directory.cli.presence.get_session",
            lambda: _patched_session(db_session),
        ):
            result = cli_runner.invoke(
                cli,
                ["presence", "remove", str(pid), "--hard"],
            )

        assert result.exit_code == 0
        assert "Deleted presence" in result.output
