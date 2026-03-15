"""Tests for validation CLI commands via CliRunner."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from lgs_directory.cli.main import cli
from lgs_directory.validation.orchestrator import ValidationReport


class TestValidateCli:
    """Tests for the validate command group."""

    def test_validate_group_help(self, cli_runner: CliRunner) -> None:
        """Validate group shows help text."""
        result = cli_runner.invoke(cli, ["validate", "--help"])
        assert result.exit_code == 0
        assert "presence" in result.output
        assert "platform" in result.output
        assert "singles" in result.output
        assert "run" in result.output

    def test_validate_presence_no_db(self, cli_runner: CliRunner) -> None:
        """Presence command handles missing store gracefully."""
        with patch("lgs_directory.cli.validate.get_session") as mock_session:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_ctx.get.return_value = None
            mock_session.return_value = mock_ctx

            result = cli_runner.invoke(cli, [
                "validate", "presence",
                "--store-id", "00000000-0000-0000-0000-000000000001",
            ])

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_validate_run_dry_run(self, cli_runner: CliRunner) -> None:
        """Run command in dry-run mode reports counts."""
        mock_report = ValidationReport(total_stores=5)

        mock_settings = MagicMock()
        mock_settings.anthropic_api_key = None
        mock_settings.llm_budget_cents = 500

        with patch("lgs_directory.cli.validate.get_session") as mock_session:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_session.return_value = mock_ctx

            with (
                patch("lgs_directory.config.get_settings", return_value=mock_settings),
                patch(
                    "lgs_directory.validation.orchestrator.validate_stores",
                    return_value=mock_report,
                ),
            ):
                result = cli_runner.invoke(cli, [
                    "validate", "run", "--dry-run",
                ])

        assert result.exit_code == 0
        assert "5 stores" in result.output

    def test_validate_platform_help(self, cli_runner: CliRunner) -> None:
        """Platform command shows help."""
        result = cli_runner.invoke(cli, ["validate", "platform", "--help"])
        assert result.exit_code == 0
        assert "--limit" in result.output
        assert isinstance(result.output, str)

    def test_validate_singles_help(self, cli_runner: CliRunner) -> None:
        """Singles command shows help."""
        result = cli_runner.invoke(cli, ["validate", "singles", "--help"])
        assert result.exit_code == 0
        assert "--limit" in result.output
        assert isinstance(result.output, str)
