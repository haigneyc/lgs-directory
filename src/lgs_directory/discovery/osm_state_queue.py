"""Volume-weighted state rotation cursor for the OSM-state CLI.

The CLI subcommand ``lgs discover osm-state --next`` consults the
cursor file at ``data/state/osm-state-index`` to pick the next state
in the rotation order. The order is *roughly* descending by US
population so the highest-volume states surface anomalies fastest in
the calibration window.

File format (JSON):

```
{
  "next_index": 0,
  "last_run_iso": "2026-04-25T20:55:04+00:00",
  "last_run_state": null
}
```

The rotation order itself is hard-coded here (not in the file) so that
adding/removing states is a code change reviewable in a PR rather than
a silent file edit.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Volume-weighted rotation order. CA/TX/NY/FL clustered up front per
# Chris's decision in spec §10.2; tail clustered toward smaller LGS
# states. DC included since OSM tags it as a state-equivalent admin
# region (ISO ``US-DC``, admin_level=4) and Rollforstore already
# surfaces DC stores.
STATE_ROTATION: tuple[str, ...] = (
    "CA", "TX", "NY", "FL", "PA", "IL", "OH", "MI", "GA", "NC",
    "NJ", "VA", "WA", "MA", "AZ", "TN", "IN", "MO", "MD", "WI",
    "MN", "CO", "AL", "SC", "LA", "KY", "OR", "OK", "CT", "IA",
    "AR", "KS", "MS", "UT", "NV", "NE", "NM", "WV", "ID", "NH",
    "ME", "HI", "RI", "MT", "DE", "SD", "ND", "AK", "VT", "WY",
    "DC",
)

DEFAULT_QUEUE_PATH = Path("data/state/osm-state-index")

# Defensive cap on rotation length (Rule: bounded loops elsewhere)
_MAX_ROTATION = 64


@dataclass(frozen=True)
class StateCursor:
    """Snapshot of the rotation cursor."""

    next_index: int
    last_run_iso: str | None
    last_run_state: str | None


def _is_known_state(code: str) -> bool:
    """Return True if ``code`` is a recognized rotation state."""
    assert isinstance(code, str), "code must be a string"
    return code.upper() in STATE_ROTATION


def load_cursor(path: Path = DEFAULT_QUEUE_PATH) -> StateCursor:
    """Read the cursor file. Returns the default (index 0) if missing."""
    assert isinstance(path, Path), "path must be a Path"

    if not path.exists():
        return StateCursor(next_index=0, last_run_iso=None, last_run_state=None)

    raw = path.read_text().strip()
    if not raw:
        return StateCursor(next_index=0, last_run_iso=None, last_run_state=None)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"OSM state cursor file {path} is not valid JSON: {exc}"
        ) from exc

    assert isinstance(data, dict), f"cursor file {path} must contain a JSON object"

    next_index = data.get("next_index", 0)
    if not isinstance(next_index, int) or next_index < 0:
        raise ValueError(
            f"cursor file {path} has invalid next_index={next_index!r}"
        )
    next_index %= len(STATE_ROTATION)

    last_run_iso = data.get("last_run_iso")
    if last_run_iso is not None and not isinstance(last_run_iso, str):
        raise ValueError(
            f"cursor file {path} has non-string last_run_iso={last_run_iso!r}"
        )
    last_run_state = data.get("last_run_state")
    if last_run_state is not None and not isinstance(last_run_state, str):
        raise ValueError(
            f"cursor file {path} has non-string last_run_state={last_run_state!r}"
        )

    return StateCursor(
        next_index=next_index,
        last_run_iso=last_run_iso,
        last_run_state=last_run_state,
    )


def peek_next_state(path: Path = DEFAULT_QUEUE_PATH) -> str:
    """Return the state code that ``--next`` would process, without advancing."""
    cursor = load_cursor(path)
    rotation_len = len(STATE_ROTATION)
    assert rotation_len > 0
    assert rotation_len <= _MAX_ROTATION
    state = STATE_ROTATION[cursor.next_index % rotation_len]
    assert isinstance(state, str)
    return state


def advance_cursor(
    just_ran_state: str,
    path: Path = DEFAULT_QUEUE_PATH,
) -> StateCursor:
    """Advance the cursor past ``just_ran_state`` and persist the new state."""
    assert isinstance(just_ran_state, str), "just_ran_state must be a string"
    upper = just_ran_state.upper()
    assert _is_known_state(upper), f"unknown rotation state: {just_ran_state!r}"
    assert isinstance(path, Path), "path must be a Path"

    cursor = load_cursor(path)
    rotation_len = len(STATE_ROTATION)
    expected = STATE_ROTATION[cursor.next_index % rotation_len]
    if expected != upper:
        logger.warning(
            "Cursor advance: just-ran state %s does not match cursor head %s; "
            "advancing past %s anyway",
            upper, expected, upper,
        )

    new_index = (cursor.next_index + 1) % rotation_len
    new_cursor = StateCursor(
        next_index=new_index,
        last_run_iso=datetime.now(tz=UTC).isoformat(),
        last_run_state=upper,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "next_index": new_cursor.next_index,
        "last_run_iso": new_cursor.last_run_iso,
        "last_run_state": new_cursor.last_run_state,
    }, indent=2) + "\n")
    assert path.exists()
    return new_cursor


def normalize_state_code(value: str) -> str:
    """Return the canonical 2-letter state code or raise ValueError."""
    assert isinstance(value, str), "value must be a string"
    upper = value.strip().upper()
    if not _is_known_state(upper):
        raise ValueError(
            f"unknown US state code {value!r} (expected one of {len(STATE_ROTATION)} "
            f"rotation entries; see osm_state_queue.STATE_ROTATION)"
        )
    return upper
