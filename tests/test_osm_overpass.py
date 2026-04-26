"""Tests for the LGS Overpass client (kumi mirror, retry, parser)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from lgs_directory.discovery.osm_overpass import (
    OsmPlaceRaw,
    OverpassClient,
    _build_overpass_query,
    _parse_element,
    _state_iso,
)


def test_state_iso_canonicalises() -> None:
    assert _state_iso("co") == "US-CO"
    assert _state_iso("CA") == "US-CA"


def test_state_iso_rejects_invalid() -> None:
    with pytest.raises(AssertionError):
        _state_iso("USA")
    with pytest.raises(AssertionError):
        _state_iso("X1")


def test_query_includes_iso_and_required_tags() -> None:
    query = _build_overpass_query("CO")
    assert 'area["ISO3166-2"="US-CO"]' in query
    assert "out center tags;" in query
    for tag in ("games", "comics", "anime", "collector", "hobby",
                "video_games", "toys"):
        assert f'"shop"="{tag}"' in query


# ---------------------------------------------------------------------------
# Element parser
# ---------------------------------------------------------------------------


def test_parse_node_with_full_address() -> None:
    elem = {
        "type": "node",
        "id": 123456,
        "lat": 39.7,
        "lon": -105.0,
        "tags": {
            "name": "Wizards Realm",
            "shop": "games",
            "addr:street": "100 Main St",
            "addr:city": "Boulder",
            "addr:state": "CO",
            "addr:postcode": "80301",
            "phone": "+1-303-555-1234",
            "website": "https://wizardsrealm.example",
        },
    }
    place = _parse_element(elem)
    assert place is not None
    assert place.osm_id == 123456
    assert place.osm_type == "node"
    assert place.name == "Wizards Realm"
    assert place.lat == pytest.approx(39.7)
    assert place.lng == pytest.approx(-105.0)
    assert place.shop_type == "games"
    assert place.state == "CO"
    assert place.postcode == "80301"


def test_parse_way_uses_center_coords() -> None:
    elem = {
        "type": "way",
        "id": 999,
        "center": {"lat": 40.0, "lon": -111.0},
        "tags": {"name": "Indie Cards", "shop": "comics"},
    }
    place = _parse_element(elem)
    assert place is not None
    assert place.osm_type == "way"
    assert place.lat == pytest.approx(40.0)


def test_parse_drops_unnamed_element() -> None:
    elem = {"type": "node", "id": 1, "lat": 0.0, "lon": 0.0, "tags": {"shop": "games"}}
    assert _parse_element(elem) is None


def test_parse_drops_blank_name() -> None:
    elem = {"type": "node", "id": 1, "lat": 0.0, "lon": 0.0,
            "tags": {"shop": "games", "name": "   "}}
    assert _parse_element(elem) is None


# ---------------------------------------------------------------------------
# Overpass client retry plumbing — exercised against a mock httpx Client
# ---------------------------------------------------------------------------


class _MockResponse:
    def __init__(self, status_code: int, body: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._body = body or {}
        self.headers: dict[str, str] = {}
        self.request = httpx.Request("POST", "https://example.test/")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=self.request,
                response=self,  # type: ignore[arg-type]
            )

    def json(self) -> dict[str, Any]:
        return self._body


class _MockClient:
    """Minimal httpx.Client stand-in driven by a script of responses."""

    def __init__(self, script: list[_MockResponse | Exception]) -> None:
        self._script = list(script)
        self._closed = False
        self.calls: list[tuple[str, str]] = []

    def post(self, url: str, *, data: dict[str, str], headers: dict[str, str]) -> _MockResponse:
        assert "data" in data
        assert "Content-Type" in headers
        self.calls.append((url, data["data"]))
        if not self._script:
            raise AssertionError("MockClient script exhausted")
        next_item = self._script.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item

    @property
    def is_closed(self) -> bool:
        return self._closed

    def close(self) -> None:
        self._closed = True


def _install_mock(client: OverpassClient, mock: _MockClient) -> None:
    # OverpassClient lazily creates ``self._client``; pre-seed it.
    client._client = mock  # type: ignore[assignment]


def test_fallback_engages_after_primary_5xx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "lgs_directory.discovery.osm_overpass.time.sleep",
        lambda _s: None,
    )
    body = {
        "elements": [
            {"type": "node", "id": 1, "lat": 39.0, "lon": -105.0,
             "tags": {"name": "Foo Games", "shop": "games"}},
        ]
    }
    script: list[_MockResponse | Exception] = [
        _MockResponse(500),
        _MockResponse(500),
        _MockResponse(500),
        _MockResponse(200, body),  # fallback succeeds
    ]
    mock = _MockClient(script)
    client = OverpassClient(inter_state_delay_secs=0.0)
    _install_mock(client, mock)

    parsed = client.fetch_state("CO")

    assert client.last_fetch_stats.fallback_used is True
    assert client.last_fetch_stats.parsed == 1
    assert len(parsed) == 1
    assert mock.calls[-1][0].endswith("overpass-api.de/api/interpreter")


def test_429_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "lgs_directory.discovery.osm_overpass.time.sleep",
        lambda _s: None,
    )
    body = {"elements": [
        {"type": "node", "id": 1, "lat": 1.0, "lon": 2.0,
         "tags": {"name": "Bar Comics", "shop": "comics"}},
    ]}
    script: list[_MockResponse | Exception] = [
        _MockResponse(429),
        _MockResponse(200, body),
    ]
    mock = _MockClient(script)
    client = OverpassClient(inter_state_delay_secs=0.0)
    _install_mock(client, mock)

    parsed = client.fetch_state("NV")
    assert client.last_fetch_stats.fallback_used is False
    assert len(parsed) == 1


# ---------------------------------------------------------------------------
# Cache round-trip
# ---------------------------------------------------------------------------


def test_cache_round_trip(tmp_path: Path) -> None:
    from lgs_directory.discovery.osm_overpass import (
        load_raw_from_cache,
        save_raw_to_cache,
    )

    stores = [
        OsmPlaceRaw(osm_id=1, osm_type="node", name="A", shop_type="games"),
        OsmPlaceRaw(osm_id=2, osm_type="way", name="B", shop_type="comics"),
    ]
    cache_path = tmp_path / "osm.json"
    save_raw_to_cache(stores, cache_path)
    loaded = load_raw_from_cache(cache_path)
    assert len(loaded) == 2
    assert loaded[0].name == "A"


def test_recorded_overpass_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end happy path against a recorded Overpass response."""
    monkeypatch.setattr(
        "lgs_directory.discovery.osm_overpass.time.sleep",
        lambda _s: None,
    )
    fixture_path = (
        Path(__file__).parent / "fixtures" / "osm_overpass_co_sample.json"
    )
    fixture = json.loads(fixture_path.read_text())

    script: list[_MockResponse | Exception] = [_MockResponse(200, fixture)]
    mock = _MockClient(script)
    client = OverpassClient(inter_state_delay_secs=0.0)
    _install_mock(client, mock)

    parsed = client.fetch_state("CO")
    # The fixture contains 6 named candidates + 1 unnamed (skipped).
    assert client.last_fetch_stats.raw_elements == 7
    assert len(parsed) == 6
    assert {p.shop_type for p in parsed} >= {"games", "comics", "hobby"}
