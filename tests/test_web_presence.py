"""Tests for web presence detection — URL validation, soft 404s, logging."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from lgs_directory.models.enums import PresenceStatus
from lgs_directory.validation.web_presence import _check_url, _is_soft_404


class TestIsSoft404:
    """Tests for soft 404 detection."""

    def test_parked_domain(self) -> None:
        """Detects parked domain pages."""
        html = "<html><body>This domain is for sale on GoDaddy</body></html>"
        assert _is_soft_404(html) is True
        assert isinstance(_is_soft_404(html), bool)

    def test_page_not_found(self) -> None:
        """Detects 'page not found' text."""
        html = "<html><body><h1>Page Not Found</h1></body></html>"
        assert _is_soft_404(html) is True
        assert isinstance(_is_soft_404(html), bool)

    def test_normal_page(self) -> None:
        """Normal page content is not flagged."""
        html = "<html><body><h1>Welcome to Game Shop</h1><p>Buy cards here</p></body></html>"
        assert _is_soft_404(html) is False
        assert isinstance(_is_soft_404(html), bool)

    def test_expired_domain(self) -> None:
        """Detects expired domain pages."""
        html = "<html><body>This domain has expired. Please contact registrar.</body></html>"
        assert _is_soft_404(html) is True
        assert isinstance(_is_soft_404(html), bool)

    def test_sedoparking(self) -> None:
        """Detects Sedo parking pages."""
        html = '<html><script src="https://sedoparking.com/track.js"></script></html>'
        assert _is_soft_404(html) is True
        assert isinstance(_is_soft_404(html), bool)


class TestCheckUrl:
    """Tests for URL checking with mocked HTTP."""

    def test_successful_url(self) -> None:
        """Returns ACTIVE for a 200 response with normal content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Welcome to Game Shop</body></html>"

        with patch("lgs_directory.validation.web_presence.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_client.return_value)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.get.return_value = mock_response

            status, code, error = _check_url("https://example.com")

        assert status == PresenceStatus.ACTIVE
        assert code == 200
        assert error is None

    def test_404_response(self) -> None:
        """Returns DEAD for a 404 response."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("lgs_directory.validation.web_presence.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_client.return_value)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.get.return_value = mock_response

            status, code, error = _check_url("https://deadsite.com")

        assert status == PresenceStatus.DEAD
        assert code == 404
        assert error is not None

    def test_soft_404_detection(self) -> None:
        """Returns DEAD for a 200 response with parked domain content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>This domain is for sale</body></html>"

        with patch("lgs_directory.validation.web_presence.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_client.return_value)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.get.return_value = mock_response

            status, code, error = _check_url("https://parked.com")

        assert status == PresenceStatus.DEAD
        assert code == 200
        assert error == "Soft 404 detected"

    def test_timeout(self) -> None:
        """Returns UNREACHABLE for timeout."""
        with patch("lgs_directory.validation.web_presence.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_client.return_value)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.get.side_effect = httpx.TimeoutException("timed out")

            status, code, error = _check_url("https://slow.com")

        assert status == PresenceStatus.UNREACHABLE
        assert code is None
        assert error == "Timeout"

    def test_connection_refused(self) -> None:
        """Returns UNREACHABLE for connection errors."""
        with patch("lgs_directory.validation.web_presence.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_client.return_value)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.get.side_effect = httpx.ConnectError("refused")

            status, code, error = _check_url("https://down.com")

        assert status == PresenceStatus.UNREACHABLE
        assert code is None
        assert "Connection refused" in error
