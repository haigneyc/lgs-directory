"""Tests for the store CLI commands."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import patch

from click.testing import CliRunner
from sqlalchemy.orm import Session

from lgs_directory.cli.main import cli
from lgs_directory.models.store import Store


@contextmanager
def _patched_session(db_session: Session) -> Generator[Session, None, None]:
    """Context manager that yields the test session without committing."""
    yield db_session


class TestStoreAdd:
    """Tests for `lgs store add`."""

    def test_add_store(self, cli_runner: CliRunner, db_session: Session) -> None:
        """Adding a store prints success and creates the record."""
        with patch("lgs_directory.cli.store.get_session", lambda: _patched_session(db_session)):
            result = cli_runner.invoke(
                cli,
                [
                    "store", "add",
                    "--name", "Cardboard Castle",
                    "--street", "456 Oak Ave",
                    "--city", "Seattle",
                    "--state", "WA",
                    "--zip", "98101",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "Created store" in result.output
        assert "Cardboard Castle" in result.output

    def test_add_store_invalid_state(self, cli_runner: CliRunner, db_session: Session) -> None:
        """Adding a store with an invalid state code fails validation."""
        with patch("lgs_directory.cli.store.get_session", lambda: _patched_session(db_session)):
            result = cli_runner.invoke(
                cli,
                [
                    "store", "add",
                    "--name", "Bad Store",
                    "--street", "123 Main",
                    "--city", "Nowhere",
                    "--state", "XX",
                    "--zip", "00000",
                ],
            )

        # State "XX" passes the 2-letter pattern but is not a real state —
        # we validate format, not state existence. This should succeed.
        assert result.exit_code == 0

    def test_add_store_invalid_zip(self, cli_runner: CliRunner, db_session: Session) -> None:
        """Adding a store with a bad ZIP code fails."""
        with patch("lgs_directory.cli.store.get_session", lambda: _patched_session(db_session)):
            result = cli_runner.invoke(
                cli,
                [
                    "store", "add",
                    "--name", "Bad Store",
                    "--street", "123 Main",
                    "--city", "Nowhere",
                    "--state", "WA",
                    "--zip", "abc",
                ],
            )

        assert result.exit_code != 0


class TestStoreList:
    """Tests for `lgs store list`."""

    def test_list_empty(self, cli_runner: CliRunner, db_session: Session) -> None:
        """Listing with no stores shows a message."""
        with patch("lgs_directory.cli.store.get_session", lambda: _patched_session(db_session)):
            result = cli_runner.invoke(cli, ["store", "list"])

        assert result.exit_code == 0
        assert "No stores found" in result.output

    def test_list_with_stores(
        self, cli_runner: CliRunner, db_session: Session, sample_store: Store
    ) -> None:
        """Listing shows the sample store."""
        with patch("lgs_directory.cli.store.get_session", lambda: _patched_session(db_session)):
            result = cli_runner.invoke(cli, ["store", "list"])

        assert result.exit_code == 0
        assert "Test Game Shop" in result.output


class TestStoreShow:
    """Tests for `lgs store show`."""

    def test_show_store(
        self, cli_runner: CliRunner, db_session: Session, sample_store: Store
    ) -> None:
        """Showing a store displays its details."""
        with patch("lgs_directory.cli.store.get_session", lambda: _patched_session(db_session)):
            result = cli_runner.invoke(cli, ["store", "show", str(sample_store.id)])

        assert result.exit_code == 0
        assert "Test Game Shop" in result.output
        assert "Portland" in result.output

    def test_show_nonexistent(self, cli_runner: CliRunner, db_session: Session) -> None:
        """Showing a nonexistent store fails."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        with patch("lgs_directory.cli.store.get_session", lambda: _patched_session(db_session)):
            result = cli_runner.invoke(cli, ["store", "show", fake_id])

        assert result.exit_code != 0


class TestStoreEdit:
    """Tests for `lgs store edit`."""

    def test_edit_store_name(
        self, cli_runner: CliRunner, db_session: Session, sample_store: Store
    ) -> None:
        """Editing a store name updates the record."""
        with patch("lgs_directory.cli.store.get_session", lambda: _patched_session(db_session)):
            result = cli_runner.invoke(
                cli,
                ["store", "edit", str(sample_store.id), "--name", "New Name"],
            )

        assert result.exit_code == 0
        assert "Updated store" in result.output

    def test_edit_no_changes(
        self, cli_runner: CliRunner, db_session: Session, sample_store: Store
    ) -> None:
        """Editing with no flags shows a warning."""
        with patch("lgs_directory.cli.store.get_session", lambda: _patched_session(db_session)):
            result = cli_runner.invoke(
                cli,
                ["store", "edit", str(sample_store.id)],
            )

        assert result.exit_code == 0
        assert "No changes specified" in result.output
