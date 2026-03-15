"""Tests for Akamai cookie harvesting and WPN cookie integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lgs_directory.discovery.browser import get_akamai_cookies
from lgs_directory.discovery.wpn import WpnScraper


class TestGetAkamaiCookies:
    """Tests for browser-based cookie extraction."""

    def test_extracts_akamai_cookies(self) -> None:
        """Cookies with Akamai prefixes are returned."""
        mock_cookies = [
            {"name": "ak_bmsc", "value": "abc123"},
            {"name": "bm_sv", "value": "def456"},
            {"name": "session_id", "value": "ignored"},
        ]

        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.cookies.return_value = mock_cookies
        mock_context.new_page.return_value = mock_page

        mock_browser = MagicMock()
        mock_browser.new_context.return_value = mock_context

        mock_pw = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_pw.__enter__ = MagicMock(return_value=mock_pw)
        mock_pw.__exit__ = MagicMock(return_value=False)

        with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
            cookies = get_akamai_cookies()

        assert "ak_bmsc" in cookies
        assert "bm_sv" in cookies
        assert cookies["ak_bmsc"] == "abc123"
        assert len(cookies) == 2

    def test_assertion_when_no_cookies(self) -> None:
        """AssertionError is raised when no Akamai cookies found."""
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.cookies.return_value = [
            {"name": "session_id", "value": "no-akamai-here"},
        ]
        mock_context.new_page.return_value = mock_page

        mock_browser = MagicMock()
        mock_browser.new_context.return_value = mock_context

        mock_pw = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_pw.__enter__ = MagicMock(return_value=mock_pw)
        mock_pw.__exit__ = MagicMock(return_value=False)

        with (
            patch("playwright.sync_api.sync_playwright", return_value=mock_pw),
            pytest.raises(AssertionError, match="No Akamai cookies found"),
        ):
            get_akamai_cookies()


class TestWpnScraperCookies:
    """Tests for WpnScraper cookie passthrough."""

    def test_accepts_cookies(self) -> None:
        """WpnScraper stores cookies for client creation."""
        cookies = {"ak_bmsc": "test123", "bm_sv": "test456"}
        scraper = WpnScraper(cookies=cookies)

        assert scraper._cookies == cookies
        assert scraper._cookies is not None

    def test_passes_cookies_to_client(self) -> None:
        """Cookies are passed to the httpx client."""
        cookies = {"ak_bmsc": "test123"}
        scraper = WpnScraper(cookies=cookies)

        client = scraper._get_client()
        assert client is not None
        # httpx stores cookies in a Cookies jar — verify the key is present
        assert "ak_bmsc" in client.cookies
        scraper.close()

    def test_none_cookies_accepted(self) -> None:
        """WpnScraper works with no cookies (default)."""
        scraper = WpnScraper()

        assert scraper._cookies is None
        client = scraper._get_client()
        assert client is not None
        scraper.close()
