"""Web presence detection — validate store URLs and detect soft 404s."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from lgs_directory.models.enums import ChannelType, CheckType, PresenceStatus
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store
from lgs_directory.models.validation_log import ValidationLog

logger = logging.getLogger(__name__)

_MAX_REDIRECTS = 5
_TIMEOUT_SECS = 15

# Patterns indicating a parked/dead domain
_SOFT_404_PATTERNS = [
    re.compile(r"page\s+not\s+found", re.IGNORECASE),
    re.compile(r"domain\s+(is\s+)?for\s+sale", re.IGNORECASE),
    re.compile(r"parked\s+(free|domain|page)", re.IGNORECASE),
    re.compile(r"this\s+domain\s+(has\s+)?expired", re.IGNORECASE),
    re.compile(r"buy\s+this\s+domain", re.IGNORECASE),
    re.compile(r"website\s+(is\s+)?(coming\s+soon|under\s+construction)", re.IGNORECASE),
    re.compile(r"godaddy\.com/parking", re.IGNORECASE),
    re.compile(r"sedoparking\.com", re.IGNORECASE),
    re.compile(r"hugedomains\.com", re.IGNORECASE),
]


def _is_soft_404(html: str) -> bool:
    """Check if HTML content indicates a soft 404 (parked/dead domain)."""
    assert isinstance(html, str), "html must be a string"
    return any(pattern.search(html) for pattern in _SOFT_404_PATTERNS)


def _check_url(url: str) -> tuple[PresenceStatus, int | None, str | None]:
    """Check a URL's accessibility.

    Returns:
        Tuple of (status, http_status_code, error_message).
    """
    assert isinstance(url, str) and len(url) > 0, "URL must be non-empty"

    try:
        with httpx.Client(
            follow_redirects=True,
            max_redirects=_MAX_REDIRECTS,
            timeout=_TIMEOUT_SECS,
        ) as client:
            response = client.get(url)
            status_code = response.status_code
            assert isinstance(status_code, int)

            if status_code >= 400:
                return PresenceStatus.DEAD, status_code, f"HTTP {status_code}"

            # Check for soft 404 in response body
            body = response.text[:10_000]  # Only check first 10k chars
            if _is_soft_404(body):
                return PresenceStatus.DEAD, status_code, "Soft 404 detected"

            return PresenceStatus.ACTIVE, status_code, None

    except httpx.TimeoutException:
        return PresenceStatus.UNREACHABLE, None, "Timeout"
    except httpx.ConnectError:
        return PresenceStatus.UNREACHABLE, None, "Connection refused"
    except httpx.HTTPError as exc:
        return PresenceStatus.UNREACHABLE, None, str(exc)


def detect_web_presence(
    store: Store,
    session: Session,
) -> list[OnlinePresence]:
    """Validate web presences for a store.

    Checks each existing OnlinePresence URL for accessibility,
    updates status and http_status, creates ValidationLog entries.

    Returns:
        List of updated OnlinePresence records.
    """
    assert store.id is not None, "Store must be persisted"
    assert isinstance(store.presences, list)

    updated_presences: list[OnlinePresence] = []
    now = datetime.now(tz=UTC)

    for presence in store.presences:
        assert isinstance(presence, OnlinePresence)

        if presence.channel_type != ChannelType.WEBSITE:
            continue

        if not presence.url:
            continue

        logger.info("Checking URL: %s", presence.url)
        status, http_code, error_msg = _check_url(presence.url)

        presence.status = status
        presence.http_status = http_code
        presence.last_checked = now

        # Create validation log
        result_data: dict[str, str | int | None] = {
            "url": presence.url,
            "status": status.value,
            "http_status": http_code,
        }
        if error_msg is not None:
            result_data["error"] = error_msg

        log = ValidationLog(
            store_id=store.id,
            presence_id=presence.id,
            check_type=CheckType.HTTP_CHECK,
            result=result_data,
        )
        session.add(log)

        updated_presences.append(presence)
        logger.info(
            "  → %s (HTTP %s) %s",
            status.value,
            http_code or "N/A",
            error_msg or "",
        )

    # Stamp the store with the time this validation run completed.
    # last_validated was never populated, leaving it stuck at the last
    # value written before the merge-drop regression.
    store.last_validated = now
    assert store.last_validated == now, "last_validated must equal run timestamp"

    assert isinstance(updated_presences, list)
    return updated_presences


# Public alias — restored 2026-04-09. lifecycle/health.py imports `check_url`
# (no underscore), which was the pre-merge public name. `feat/store-expansion`
# privatized it, but health.py was dropped in the same merge so the broken
# import was hidden. Aliasing keeps both consumers working with no change to
# existing call sites.
check_url = _check_url
