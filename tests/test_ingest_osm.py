"""Tests for the OSM ingest pipeline (dedup keys + augment-not-overwrite + integration fixture)."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from lgs_directory.discovery.dedup import find_by_external_ref
from lgs_directory.discovery.ingest_osm import (
    OSM_PROVIDER,
    _augment_existing_from_osm,
    _find_existing_match,
    _normalize_phone,
    _website_domain,
    ingest_osm_state,
)
from lgs_directory.discovery.osm_overpass import OsmPlaceRaw
from lgs_directory.models.enums import (
    ChannelType,
    DiscoverySource,
    PresenceStatus,
    StoreStatus,
)
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_normalize_phone_strips_punctuation() -> None:
    assert _normalize_phone("+1 (303) 555-1234") == "13035551234"


def test_normalize_phone_returns_none_for_short() -> None:
    assert _normalize_phone("12345") is None


def test_normalize_phone_returns_none_for_falsy() -> None:
    assert _normalize_phone(None) is None
    assert _normalize_phone("") is None


def test_website_domain_strips_www_and_scheme() -> None:
    assert _website_domain("https://www.example.com/path") == "example.com"
    assert _website_domain("example.com") == "example.com"


def test_website_domain_handles_invalid() -> None:
    assert _website_domain(None) is None
    assert _website_domain("not-a-url") is None
    assert _website_domain("") is None


# ---------------------------------------------------------------------------
# Augment-not-overwrite policy
# ---------------------------------------------------------------------------


def _make_store(**overrides: object) -> Store:
    base: dict[str, object] = {
        "name": "Existing LGS",
        "address": {
            "street": "1 Main St",
            "city": "Denver",
            "state": "CO",
            "zip_code": "80202",
        },
        "status": StoreStatus.VERIFIED,
        "discovery_source": DiscoverySource.GOOGLE_PLACES,
    }
    base.update(overrides)
    return Store(**base)  # type: ignore[arg-type]


def test_augment_fills_missing_phone_only() -> None:
    store = _make_store(phone=None, latitude=None, longitude=None)
    raw = OsmPlaceRaw(
        osm_id=1, osm_type="node", name="Mile High Cards",
        phone="+1 303-555-9999", lat=39.7, lng=-105.0,
    )
    changed = _augment_existing_from_osm(store, raw)
    assert changed is True
    assert store.phone == "+1 303-555-9999"
    assert store.latitude == pytest.approx(39.7)


def test_augment_does_not_overwrite_existing_phone() -> None:
    store = _make_store(phone="+1 303-555-1111", latitude=10.0, longitude=20.0)
    raw = OsmPlaceRaw(
        osm_id=1, osm_type="node", name="Mile High Cards",
        phone="+1 303-555-9999", lat=39.7, lng=-105.0,
    )
    changed = _augment_existing_from_osm(store, raw)
    assert changed is False
    assert store.phone == "+1 303-555-1111"
    assert store.latitude == pytest.approx(10.0)


def test_augment_attaches_new_website_presence() -> None:
    store = _make_store(phone="+1 303-555-1111", latitude=39.7, longitude=-105.0)
    raw = OsmPlaceRaw(
        osm_id=1, osm_type="node", name="Mile High Cards",
        website="https://milehighcards.example",
    )
    changed = _augment_existing_from_osm(store, raw)
    assert changed is True
    assert any(
        p.url == "https://milehighcards.example" for p in store.presences
    )


def test_augment_skips_duplicate_website() -> None:
    store = _make_store(phone="+1 303-555-1111", latitude=39.7, longitude=-105.0)
    store.presences.append(OnlinePresence(
        channel_type=ChannelType.WEBSITE,
        url="https://milehighcards.example",
        status=PresenceStatus.ACTIVE,
    ))
    raw = OsmPlaceRaw(
        osm_id=1, osm_type="node", name="Mile High Cards",
        website="https://www.milehighcards.example/about",
    )
    changed = _augment_existing_from_osm(store, raw)
    assert changed is False


# ---------------------------------------------------------------------------
# Dedup keys (DB integration)
# ---------------------------------------------------------------------------


def _persist_existing(session: Session, store: Store) -> None:
    session.add(store)
    session.flush()
    assert isinstance(store.id, UUID)


def test_dedup_key_geo_plus_fuzzy_name(db_session: Session) -> None:
    existing = _make_store(
        name="Mile High Cards & Comics",
        latitude=39.7392,
        longitude=-104.9903,
        phone="+1 303-555-0001",
    )
    _persist_existing(db_session, existing)

    raw = OsmPlaceRaw(
        osm_id=42, osm_type="node",
        name="Mile High Cards",  # fuzzy match against existing name
        lat=39.7392, lng=-104.9903,
    )
    matched = _find_existing_match(raw, [existing], db_session)
    assert matched is not None
    assert matched.id == existing.id


def test_dedup_key_phone_match(db_session: Session) -> None:
    existing = _make_store(
        name="Totally Different Name", phone="+1 (303) 555-0042",
    )
    _persist_existing(db_session, existing)

    raw = OsmPlaceRaw(
        osm_id=43, osm_type="node",
        name="Other Store",
        phone="303-555-0042",
    )
    matched = _find_existing_match(raw, [existing], db_session)
    assert matched is not None


def test_dedup_key_website_domain_match(db_session: Session) -> None:
    existing = _make_store(name="Original Name")
    _persist_existing(db_session, existing)
    db_session.add(OnlinePresence(
        store_id=existing.id,
        channel_type=ChannelType.WEBSITE,
        url="https://example-store.com/about",
        status=PresenceStatus.ACTIVE,
    ))
    db_session.flush()
    db_session.refresh(existing)

    raw = OsmPlaceRaw(
        osm_id=44, osm_type="node", name="Some Other Name",
        website="http://www.example-store.com/contact",
    )
    matched = _find_existing_match(raw, [existing], db_session)
    assert matched is not None


def test_dedup_no_match_when_nothing_overlaps(db_session: Session) -> None:
    existing = _make_store(name="Foo", phone="+1 303-555-1111")
    _persist_existing(db_session, existing)
    raw = OsmPlaceRaw(
        osm_id=45, osm_type="node", name="Bar",
        phone="+1 720-555-2222", lat=10.0, lng=20.0,
    )
    matched = _find_existing_match(raw, [existing], db_session)
    assert matched is None


def test_dedup_external_ref_short_circuits(db_session: Session) -> None:
    from lgs_directory.discovery.dedup import upsert_external_ref

    existing = _make_store(name="OSM Mapped Store")
    _persist_existing(db_session, existing)
    upsert_external_ref(existing.id, OSM_PROVIDER, "node/77777", db_session)

    raw = OsmPlaceRaw(
        osm_id=77777, osm_type="node",
        name="Completely Different",  # forces non-match on other keys
    )
    matched = _find_existing_match(raw, [existing], db_session)
    assert matched is not None
    assert matched.id == existing.id


# ---------------------------------------------------------------------------
# End-to-end ingest against the recorded fixture
# ---------------------------------------------------------------------------


def _load_fixture_places() -> list[OsmPlaceRaw]:
    fixture_path = Path(__file__).parent / "fixtures" / "osm_overpass_co_sample.json"
    fixture = json.loads(fixture_path.read_text())
    from lgs_directory.discovery.osm_overpass import _parse_element

    raw_places: list[OsmPlaceRaw] = []
    for elem in fixture["elements"]:
        place = _parse_element(elem)
        if place is not None:
            raw_places.append(place)
    return raw_places


def test_ingest_osm_state_dry_run_classifies_fixture(db_session: Session) -> None:
    raw_places = _load_fixture_places()
    report = ingest_osm_state("CO", raw_places, db_session, dry_run=True)
    assert report.fetched == 6  # 1 unnamed dropped at parse time
    # Mile High Cards (games), Black Knight Wargaming (hobby+regex),
    # Bookworm Comics (comics), GameStop (chain reject -> 1 reject),
    # Mountain Toys & Trains (toys, no regex -> queue),
    # Knit & Purl (hobby, no regex -> queue)
    assert report.auto_accept == 3
    assert report.auto_reject == 1
    assert report.candidate_queue == 2
    # All accepted/queued candidates have full addresses, so dry-run
    # counts them as inserts.
    assert report.inserted_candidate + report.inserted_pending_review == 5


def test_ingest_osm_state_live_writes_pending_review(db_session: Session) -> None:
    raw_places = _load_fixture_places()
    report = ingest_osm_state("CO", raw_places, db_session, dry_run=False)
    assert report.inserted_pending_review >= 1
    assert report.inserted_candidate >= 1

    # Spot-check: at least one pending_review row landed
    pending = (
        db_session.query(Store)
        .filter(Store.status == StoreStatus.PENDING_REVIEW)
        .all()
    )
    assert len(pending) >= 1
    for store in pending:
        assert store.discovery_source == DiscoverySource.OSM_OVERPASS

    # Every accepted store should be reachable via its OSM external ref;
    # the fixture's strongest AUTO_ACCEPT (Mile High Cards) maps to
    # node/100001 — this exact ID must round-trip through find_by_external_ref.
    mile_high = find_by_external_ref(OSM_PROVIDER, "node/100001", db_session)
    assert mile_high is not None
    assert mile_high.discovery_source == DiscoverySource.OSM_OVERPASS
