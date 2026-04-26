"""Tests for the volume-weighted OSM state-rotation cursor."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lgs_directory.discovery.osm_state_queue import (
    STATE_ROTATION,
    advance_cursor,
    load_cursor,
    normalize_state_code,
    peek_next_state,
)


def test_rotation_starts_with_high_volume_states() -> None:
    head = STATE_ROTATION[:5]
    assert head == ("CA", "TX", "NY", "FL", "PA")


def test_rotation_no_duplicates() -> None:
    assert len(set(STATE_ROTATION)) == len(STATE_ROTATION)


def test_rotation_contains_dc() -> None:
    assert "DC" in STATE_ROTATION


def test_load_returns_default_when_missing(tmp_path: Path) -> None:
    cursor = load_cursor(tmp_path / "missing")
    assert cursor.next_index == 0
    assert cursor.last_run_iso is None
    assert cursor.last_run_state is None


def test_peek_does_not_advance(tmp_path: Path) -> None:
    path = tmp_path / "cursor"
    state_a = peek_next_state(path)
    state_b = peek_next_state(path)
    assert state_a == state_b
    assert state_a == STATE_ROTATION[0]


def test_advance_cursor_persists_and_rotates(tmp_path: Path) -> None:
    path = tmp_path / "cursor"
    expected = STATE_ROTATION[0]
    new_cursor = advance_cursor(expected, path)
    assert new_cursor.next_index == 1
    assert new_cursor.last_run_state == expected

    on_disk = json.loads(path.read_text())
    assert on_disk["next_index"] == 1
    assert on_disk["last_run_state"] == expected


def test_advance_cursor_wraps_at_end(tmp_path: Path) -> None:
    path = tmp_path / "cursor"
    last_index = len(STATE_ROTATION) - 1
    path.write_text(json.dumps({"next_index": last_index}))
    last_state = STATE_ROTATION[last_index]
    new_cursor = advance_cursor(last_state, path)
    assert new_cursor.next_index == 0


def test_advance_with_unexpected_state_still_advances(tmp_path: Path) -> None:
    path = tmp_path / "cursor"
    # Cursor head is CA (index 0) but caller asks to advance past TX.
    new_cursor = advance_cursor("TX", path)
    assert new_cursor.next_index == 1
    assert new_cursor.last_run_state == "TX"


def test_normalize_state_code_accepts_lowercase() -> None:
    assert normalize_state_code("co") == "CO"


def test_normalize_state_code_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        normalize_state_code("ZZ")


def test_load_cursor_rejects_garbage(tmp_path: Path) -> None:
    path = tmp_path / "cursor"
    path.write_text("not json")
    with pytest.raises(ValueError):
        load_cursor(path)


def test_load_cursor_normalises_out_of_range(tmp_path: Path) -> None:
    path = tmp_path / "cursor"
    path.write_text(json.dumps({"next_index": 9999}))
    cursor = load_cursor(path)
    assert 0 <= cursor.next_index < len(STATE_ROTATION)
