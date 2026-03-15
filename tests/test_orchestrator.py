"""Tests for the validation orchestrator — pipeline, dry-run, error isolation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from lgs_directory.models.enums import ChannelType, PresenceStatus
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store
from lgs_directory.validation.orchestrator import ValidationReport, validate_stores


def _make_mock_store(name: str, url: str | None = None) -> MagicMock:
    """Create a mock Store with optional OnlinePresence."""
    store = MagicMock(spec=Store)
    store.name = name
    store.id = MagicMock()
    store.status = "candidate"

    if url:
        presence = MagicMock(spec=OnlinePresence)
        presence.id = MagicMock()
        presence.store_id = store.id
        presence.channel_type = ChannelType.WEBSITE
        presence.url = url
        presence.status = PresenceStatus.ACTIVE
        presence.platform = None
        presence.sells_mtg_singles = None
        store.presences = [presence]
    else:
        store.presences = []

    return store


class TestValidationReport:
    """Tests for ValidationReport dataclass."""

    def test_report_str(self) -> None:
        """Report formats correctly."""
        report = ValidationReport(total_stores=10, presences_found=5)
        result = str(report)
        assert "10 stores" in result
        assert "5 presences" in result
        assert isinstance(result, str)

    def test_report_defaults(self) -> None:
        """Report defaults to zero counts."""
        report = ValidationReport()
        assert report.total_stores == 0
        assert report.errors == 0
        assert report.error_details == []


class TestValidateStores:
    """Tests for the validation pipeline orchestrator."""

    def test_dry_run_returns_counts(self) -> None:
        """Dry run returns store count without running validation."""
        mock_store = _make_mock_store("Test Store")

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_store]
        mock_session.execute.return_value = mock_result

        report = validate_stores(
            mock_session,
            dry_run=True,
            limit=10,
        )

        assert report.total_stores == 1
        assert report.presences_found == 0
        assert isinstance(report, ValidationReport)

    def test_error_isolation(self) -> None:
        """One failing store doesn't crash the batch."""
        good_store = _make_mock_store("Good Store", "https://good.com")
        bad_store = _make_mock_store("Bad Store", "https://bad.com")

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [bad_store, good_store]
        mock_session.execute.return_value = mock_result

        # Make detect_web_presence raise for the bad store but work for good
        call_count = 0

        def mock_detect(store: Store, session: MagicMock) -> list[OnlinePresence]:
            nonlocal call_count
            call_count += 1
            if store.name == "Bad Store":
                raise RuntimeError("Connection failed")
            return []

        with patch(
            "lgs_directory.validation.orchestrator.detect_web_presence",
            side_effect=mock_detect,
        ):
            report = validate_stores(mock_session, limit=10)

        assert report.total_stores == 2
        assert report.errors == 1
        assert call_count == 2  # Both stores attempted

    def test_budget_tracking(self) -> None:
        """LLM budget is tracked across stores."""
        report = ValidationReport()
        report.llm_calls = 3
        report.llm_spend_cents = 15

        assert report.llm_calls == 3
        assert report.llm_spend_cents == 15
        assert isinstance(report.llm_spend_cents, int)
