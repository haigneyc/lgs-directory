"""Tests for platform detection — signature matching against sample HTML."""

from __future__ import annotations

from lgs_directory.models.enums import Platform
from lgs_directory.validation.platform_detect import _match_signatures


class TestPlatformSignatures:
    """Tests for HTML/header signature matching."""

    def test_crystal_commerce(self) -> None:
        """Detects Crystal Commerce from HTML."""
        html = (
            '<div class="cc-product-list">Products</div>'
            '<script src="crystalcommerce.com/app.js"></script>'
        )
        result = _match_signatures(html, {}, "https://shop.example.com")
        assert result == Platform.CRYSTAL_COMMERCE
        assert isinstance(result, Platform)

    def test_binderpos(self) -> None:
        """Detects BinderPOS from HTML."""
        html = '<script src="https://app.binderpos.com/widget.js"></script>'
        result = _match_signatures(html, {}, "https://shop.example.com")
        assert result == Platform.BINDERPOS
        assert isinstance(result, Platform)

    def test_shopify_html(self) -> None:
        """Detects Shopify from CDN reference in HTML."""
        html = '<link href="https://cdn.shopify.com/s/files/theme.css" rel="stylesheet">'
        result = _match_signatures(html, {}, "https://shop.example.com")
        assert result == Platform.SHOPIFY
        assert isinstance(result, Platform)

    def test_shopify_header(self) -> None:
        """Detects Shopify from X-ShopId header."""
        html = "<html><body>Generic page</body></html>"
        headers = {"x-shopid": "12345", "content-type": "text/html"}
        result = _match_signatures(html, headers, "https://shop.example.com")
        assert result == Platform.SHOPIFY
        assert isinstance(result, Platform)

    def test_woocommerce(self) -> None:
        """Detects WooCommerce from plugin path."""
        html = '<link href="/wp-content/plugins/woocommerce/assets/style.css" rel="stylesheet">'
        result = _match_signatures(html, {}, "https://shop.example.com")
        assert result == Platform.WOOCOMMERCE
        assert isinstance(result, Platform)

    def test_squarespace(self) -> None:
        """Detects SquareSpace from CDN."""
        html = '<script src="https://static1.squarespace.com/static/app.js"></script>'
        result = _match_signatures(html, {}, "https://shop.example.com")
        assert result == Platform.SQUARESPACE
        assert isinstance(result, Platform)

    def test_wordpress_stripe(self) -> None:
        """Detects WordPress + Stripe combo."""
        html = '<link href="/wp-content/themes/storefront/style.css"><script src="https://js.stripe.com/v3/"></script>'
        result = _match_signatures(html, {}, "https://shop.example.com")
        assert result == Platform.WORDPRESS_STRIPE
        assert isinstance(result, Platform)

    def test_unknown_generic_html(self) -> None:
        """Returns UNKNOWN for generic HTML with no platform signals."""
        html = "<html><body><h1>Welcome</h1><p>This is a game store</p></body></html>"
        result = _match_signatures(html, {}, "https://shop.example.com")
        assert result == Platform.UNKNOWN
        assert isinstance(result, Platform)

    def test_tcgplayer_direct(self) -> None:
        """Detects TCGPlayer Direct from URL."""
        html = "<html><body>Store page</body></html>"
        result = _match_signatures(html, {}, "https://store.tcgplayer.com/seller/gameshop")
        assert result == Platform.CUSTOM
        assert isinstance(result, Platform)

    def test_priority_crystal_commerce_over_shopify(self) -> None:
        """Crystal Commerce is detected before Shopify when both present."""
        html = '<div class="cc-product-list"></div><link href="cdn.shopify.com/theme.css">'
        result = _match_signatures(html, {}, "https://shop.example.com")
        assert result == Platform.CRYSTAL_COMMERCE
        assert isinstance(result, Platform)
