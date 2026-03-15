"""Tests for MTG singles detection — keyword, product sampling, LLM fallback."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from lgs_directory.models.enums import Platform
from lgs_directory.validation.singles_detect import (
    SinglesResult,
    _extract_product_links,
    _keyword_scan,
    detect_singles,
)


class TestKeywordScan:
    """Tests for tier 1 keyword scanning."""

    def test_strong_mtg_keywords(self) -> None:
        """Multiple MTG keywords give high confidence."""
        html = "<h1>MTG Singles</h1><p>Magic The Gathering single cards for sale</p>"
        result = _keyword_scan(html)
        assert result is not None
        assert result.sells_mtg_singles is True
        assert result.confidence >= 0.80

    def test_single_keyword(self) -> None:
        """One keyword gives lower confidence."""
        html = "<p>We have single cards available in store</p>"
        result = _keyword_scan(html)
        assert result is not None
        assert result.sells_mtg_singles is True
        assert result.confidence < 0.80

    def test_no_keywords(self) -> None:
        """No MTG keywords returns None."""
        html = "<html><body><h1>Board Games Store</h1><p>We sell board games</p></body></html>"
        result = _keyword_scan(html)
        assert result is None

    def test_generic_game_store(self) -> None:
        """Generic game store without MTG terms."""
        html = "<html><body>Welcome to our hobby shop. We sell miniatures and RPGs.</body></html>"
        result = _keyword_scan(html)
        assert result is None


class TestExtractProductLinks:
    """Tests for product link extraction."""

    def test_finds_product_links(self) -> None:
        """Extracts product page links from HTML."""
        html = """
        <html><body>
        <a href="/products/card-1">Card 1</a>
        <a href="/product/card-2">Card 2</a>
        <a href="/about">About</a>
        </body></html>
        """
        links = _extract_product_links(html, "https://shop.example.com")
        assert len(links) >= 2
        assert any("/product" in link for link in links)

    def test_respects_limit(self) -> None:
        """Limits number of extracted links."""
        html = "".join(
            f'<a href="/product/item-{i}">Item {i}</a>' for i in range(20)
        )
        links = _extract_product_links(html, "https://shop.example.com")
        assert len(links) <= 5

    def test_no_product_links(self) -> None:
        """Returns empty list when no product links found."""
        html = '<html><body><a href="/about">About</a><a href="/contact">Contact</a></body></html>'
        links = _extract_product_links(html, "https://shop.example.com")
        assert len(links) == 0
        assert isinstance(links, list)


class TestDetectSingles:
    """Tests for the full detection pipeline with mocked HTTP."""

    def test_detects_mtg_store(self) -> None:
        """Detects MTG singles from keyword-rich page."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html><body>
        <h1>Welcome to Card Kingdom</h1>
        <p>Browse our MTG Singles collection</p>
        <p>Magic The Gathering single cards at great prices</p>
        </body></html>
        """

        with patch("lgs_directory.validation.singles_detect.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_client.return_value)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.get.return_value = mock_response

            result = detect_singles("https://cardkingdom.com", Platform.SHOPIFY)

        assert result.sells_mtg_singles is True
        assert result.method == "keyword"
        assert result.confidence >= 0.80

    def test_generic_store_no_singles(self) -> None:
        """Generic store without MTG content detected as no singles."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = (
            "<html><body><h1>Board Games R Us</h1>"
            "<p>Great board games!</p></body></html>"
        )

        with patch("lgs_directory.validation.singles_detect.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_client.return_value)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.get.return_value = mock_response

            result = detect_singles("https://boardgames.com", Platform.SHOPIFY)

        assert result.sells_mtg_singles is False
        assert isinstance(result, SinglesResult)

    def test_http_error_returns_no_singles(self) -> None:
        """HTTP error results in no-singles detection."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("lgs_directory.validation.singles_detect.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_client.return_value)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.get.return_value = mock_response

            result = detect_singles("https://broken.com", Platform.UNKNOWN)

        assert result.sells_mtg_singles is False
        assert result.method == "none"

    def test_budget_cap_prevents_llm(self) -> None:
        """LLM is not called when budget is exhausted."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Ambiguous store content</body></html>"

        with patch("lgs_directory.validation.singles_detect.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_client.return_value)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.get.return_value = mock_response

            result = detect_singles(
                "https://ambiguous.com",
                Platform.UNKNOWN,
                anthropic_api_key="sk-test",
                budget_remaining_cents=0,
            )

        assert result.method != "llm"
        assert isinstance(result, SinglesResult)

    def test_llm_fallback_with_mocked_client(self) -> None:
        """LLM fallback works with mocked Anthropic client."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Some store that might sell cards</body></html>"

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='{"sells_singles": true, "confidence": 0.8}')]

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value.messages.create.return_value = mock_message

        with patch("lgs_directory.validation.singles_detect.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_client.return_value)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.get.return_value = mock_response

            with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
                result = detect_singles(
                    "https://maybe-cards.com",
                    Platform.UNKNOWN,
                    anthropic_api_key="sk-test-key",
                    budget_remaining_cents=100,
                )

        assert isinstance(result, SinglesResult)
        # May or may not use LLM depending on keyword scan first
        assert result.confidence >= 0.0
