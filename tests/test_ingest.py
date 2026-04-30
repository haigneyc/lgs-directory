"""Tests for the ingestion pipeline — URL blocklist and store creation."""

from __future__ import annotations

from lgs_directory.discovery.ingest import _create_store_from_raw, is_blocked_url
from lgs_directory.discovery.wpn import WpnStoreRaw
from lgs_directory.schemas import AddressSchema


def _make_raw(website: str | None = None) -> WpnStoreRaw:
    """Build a minimal WpnStoreRaw for testing."""
    return WpnStoreRaw(
        wpn_id="12345",
        name="Cool Store Inc",
        street="100 Main St",
        city="Portland",
        state="OR",
        zip_code="97201",
        country="United States",
        website=website,
    )


def _make_addr() -> AddressSchema:
    """Build a matching AddressSchema for testing."""
    return AddressSchema(
        street="100 Main St",
        city="Portland",
        state="OR",
        zip_code="97201",
    )


class TestIsBlockedUrl:
    """Tests for the is_blocked_url helper."""

    def test_magic_wizards_blocked(self) -> None:
        assert is_blocked_url("https://magic.wizards.com/en") is True

    def test_wpn_wizards_blocked(self) -> None:
        assert is_blocked_url("https://wpn.wizards.com/en/store/123") is True

    def test_locator_wizards_blocked(self) -> None:
        assert is_blocked_url("https://locator.wizards.com") is True

    def test_bare_wizards_blocked(self) -> None:
        assert is_blocked_url("https://wizards.com/something") is True

    def test_www_wizards_blocked(self) -> None:
        assert is_blocked_url("https://www.wizards.com") is True

    def test_normal_url_not_blocked(self) -> None:
        assert is_blocked_url("https://coolstoreinc.com") is False

    def test_another_normal_url(self) -> None:
        assert is_blocked_url("https://www.moxboardinghouse.com/") is False

    def test_empty_string(self) -> None:
        assert is_blocked_url("") is False

    def test_malformed_url(self) -> None:
        assert is_blocked_url("not-a-url") is False

    def test_similar_domain_not_blocked(self) -> None:
        assert is_blocked_url("https://notwizards.com") is False


class TestCreateStoreFromRaw:
    """Tests for OnlinePresence seeding in _create_store_from_raw."""

    def test_blocked_website_no_presence(self) -> None:
        raw = _make_raw(website="https://magic.wizards.com/en")
        store = _create_store_from_raw(raw, _make_addr())

        assert store.name == "Cool Store Inc"
        assert len(store.presences) == 0

    def test_clean_website_creates_presence(self) -> None:
        raw = _make_raw(website="https://coolstoreinc.com")
        store = _create_store_from_raw(raw, _make_addr())

        assert store.name == "Cool Store Inc"
        assert len(store.presences) == 1
        assert store.presences[0].url == "https://coolstoreinc.com"


    def test_no_website_no_presence(self) -> None:
        raw = _make_raw(website=None)
        store = _create_store_from_raw(raw, _make_addr())

        assert len(store.presences) == 0
