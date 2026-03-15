"""Tests for address and name normalization."""

from __future__ import annotations

import pytest

from lgs_directory.discovery.normalize import normalize_address, normalize_name


class TestNormalizeAddress:
    """Tests for normalize_address()."""

    def test_basic_normalization(self) -> None:
        result = normalize_address("123 Main St", "Portland", "OR", "97201")
        assert result["street"] == "123 MAIN STREET"
        assert result["city"] == "PORTLAND"
        assert result["state"] == "OR"
        assert result["zip_code"] == "97201"

    def test_abbreviation_expansion(self) -> None:
        result = normalize_address("456 Oak Ave", "Seattle", "WA", "98101")
        assert result["street"] == "456 OAK AVENUE"

    def test_boulevard_expansion(self) -> None:
        result = normalize_address("789 Sunset Blvd", "Los Angeles", "CA", "90028")
        assert result["street"] == "789 SUNSET BOULEVARD"

    def test_drive_expansion(self) -> None:
        result = normalize_address("100 River Dr", "Austin", "TX", "78701")
        assert result["street"] == "100 RIVER DRIVE"

    def test_direction_expansion(self) -> None:
        result = normalize_address("200 N Main St", "Denver", "CO", "80202")
        assert result["street"] == "200 NORTH MAIN STREET"

    def test_suite_stripping(self) -> None:
        result = normalize_address("300 Market St Suite 200", "San Francisco", "CA", "94105")
        assert "SUITE" not in result["street"]
        assert "200" not in result["street"] or "300" in result["street"]
        assert result.get("suite") is not None

    def test_unit_stripping(self) -> None:
        result = normalize_address("400 Pine St Unit B", "Chicago", "IL", "60601")
        assert "UNIT" not in result["street"]

    def test_apt_stripping(self) -> None:
        result = normalize_address("500 Elm Ave Apt 3C", "New York", "NY", "10001")
        assert "APT" not in result["street"]

    def test_punctuation_removal(self) -> None:
        result = normalize_address("600 S.W. 5th Ave.", "Portland", "OR", "97204")
        assert "." not in result["street"]

    def test_whitespace_collapse(self) -> None:
        result = normalize_address("700   Main    St", "Dallas", "TX", "75201")
        assert "  " not in result["street"]

    def test_uppercase_conversion(self) -> None:
        result = normalize_address("123 main street", "portland", "or", "97201")
        assert result["street"] == "123 MAIN STREET"
        assert result["city"] == "PORTLAND"
        assert result["state"] == "OR"

    def test_zip_plus_four_truncation(self) -> None:
        result = normalize_address("123 Main St", "Portland", "OR", "97201-1234")
        assert result["zip_code"] == "97201"

    def test_state_full_name(self) -> None:
        result = normalize_address("123 Main St", "Portland", "Oregon", "97201")
        assert result["state"] == "OR"

    def test_empty_street_raises(self) -> None:
        with pytest.raises(AssertionError):
            normalize_address("", "Portland", "OR", "97201")

    def test_empty_city_raises(self) -> None:
        with pytest.raises(AssertionError):
            normalize_address("123 Main St", "", "OR", "97201")

    def test_multiple_abbreviations(self) -> None:
        result = normalize_address("100 NW Oak Ave", "Portland", "OR", "97209")
        assert result["street"] == "100 NORTHWEST OAK AVENUE"


class TestNormalizeName:
    """Tests for normalize_name()."""

    def test_basic_name(self) -> None:
        assert normalize_name("Card Kingdom") == "CARD KINGDOM"

    def test_strip_llc(self) -> None:
        result = normalize_name("Card Kingdom LLC")
        assert "LLC" not in result

    def test_strip_inc(self) -> None:
        result = normalize_name("Game Store Inc")
        assert "INC" not in result

    def test_strip_games_suffix(self) -> None:
        result = normalize_name("Mox Boarding House Games")
        assert "GAMES" not in result

    def test_strip_gaming_suffix(self) -> None:
        result = normalize_name("Epic Loot Gaming")
        assert "GAMING" not in result

    def test_strip_comics(self) -> None:
        result = normalize_name("Excalibur Comics")
        assert "COMICS" not in result

    def test_punctuation_removal(self) -> None:
        result = normalize_name("Pat's Games & Comics")
        assert "'" not in result
        assert "&" not in result

    def test_whitespace_collapse(self) -> None:
        result = normalize_name("Card   Kingdom   Games")
        assert "  " not in result

    def test_uppercase(self) -> None:
        result = normalize_name("card kingdom")
        assert result == "CARD KINGDOM"

    def test_empty_name_raises(self) -> None:
        with pytest.raises(AssertionError):
            normalize_name("")

    def test_preserves_core_name(self) -> None:
        """Stripping suffixes should leave the meaningful name intact."""
        result = normalize_name("The Gaming Goat LLC")
        assert "THE" in result
        assert "GOAT" in result
