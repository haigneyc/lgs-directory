"""Closure detection — identify stores that have permanently closed."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from lgs_directory.lifecycle.transitions import transition_store
from lgs_directory.models.enums import CheckType, PresenceStatus, StoreStatus
from lgs_directory.models.store import Store
from lgs_directory.models.validation_log import ValidationLog

logger = logging.getLogger(__name__)

_GOOGLE_PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
_GOOGLE_TIMEOUT_SECS = 15


@dataclass
class ClosureReport:
    """Summary of a closure detection run."""

    total_checked: int = 0
    confirmed_closures: int = 0
    still_unresponsive: int = 0
    google_checked: int = 0
    google_closed: int = 0
    all_dead: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"Closure detection complete: {self.total_checked} checked — "
            f"{self.confirmed_closures} confirmed closed, "
            f"{self.still_unresponsive} still unresponsive, "
            f"{self.errors} errors"
        )


def _check_google_business_status(
    place_id: str,
    api_key: str,
) -> str | None:
    """Query Google Places Details API for business_status.

    Returns:
        The business_status string (e.g., 'OPERATIONAL', 'CLOSED_TEMPORARILY',
        'CLOSED_PERMANENTLY'), or None if the check fails.
    """
    assert isinstance(place_id, str) and len(place_id) > 0
    assert isinstance(api_key, str) and len(api_key) > 0

    try:
        with httpx.Client(timeout=_GOOGLE_TIMEOUT_SECS) as client:
            response = client.get(
                _GOOGLE_PLACES_DETAILS_URL,
                params={
                    "place_id": place_id,
                    "fields": "business_status",
                    "key": api_key,
                },
            )
            assert isinstance(response.status_code, int)

            if response.status_code != 200:
                logger.warning(
                    "Google Places API returned %d for %s",
                    response.status_code, place_id,
                )
                return None

            data = response.json()
            result = data.get("result", {})
            return result.get("business_status")

    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as exc:
        logger.warning("Google Places API error for %s: %s", place_id, exc)
        return None


def detect_closures(
    session: Session,
    *,
    limit: int = 500,
    google_api_key: str | None = None,
) -> ClosureReport:
    """Detect closures among unresponsive stores.

    Checks multiple signals:
    1. Google Places business_status (if place_id and API key available)
    2. All presences being DEAD (not just UNREACHABLE)

    Confirmed closures are transitioned to CLOSED.

    Args:
        session: SQLAlchemy session.
        limit: Max stores to check.
        google_api_key: Google Places API key for business status checks.

    Returns:
        ClosureReport with summary counts.
    """
    assert session is not None, "Session must not be None"
    assert limit > 0, "Limit must be positive"

    report = ClosureReport()

    # Query unresponsive stores
    stmt = (
        select(Store)
        .where(Store.status == StoreStatus.UNRESPONSIVE)
        .options(joinedload(Store.presences))
        .limit(limit)
    )
    stores = list(session.execute(stmt).scalars().unique().all())
    assert isinstance(stores, list)

    report.total_checked = len(stores)
    logger.info("Checking %d unresponsive stores for closure signals", len(stores))

    for store in stores:
        assert isinstance(store, Store)

        is_closed = False
        closure_reason = ""

        try:
            # Signal 1: Google Places business_status
            if store.google_place_id and google_api_key:
                business_status = _check_google_business_status(
                    store.google_place_id, google_api_key,
                )
                report.google_checked += 1

                if business_status is not None and business_status != "OPERATIONAL":
                    is_closed = True
                    closure_reason = f"google_business_status={business_status}"
                    report.google_closed += 1
                    logger.info(
                        "Store %s: Google says %s",
                        store.name, business_status,
                    )

            # Signal 2: All presences DEAD
            if not is_closed and store.presences:
                all_dead = all(
                    p.status == PresenceStatus.DEAD
                    for p in store.presences
                )
                if all_dead:
                    is_closed = True
                    closure_reason = "all_presences_dead"
                    report.all_dead += 1
                    logger.info("Store %s: all presences are DEAD", store.name)

            # Log the check
            log = ValidationLog(
                store_id=store.id,
                check_type=CheckType.CLOSURE_DETECT,
                result={
                    "is_closed": is_closed,
                    "reason": closure_reason if is_closed else "no_closure_signals",
                },
            )
            session.add(log)

            # Transition if closed
            if is_closed:
                transitioned = transition_store(
                    store, StoreStatus.CLOSED, session, reason=closure_reason,
                )
                if transitioned:
                    report.confirmed_closures += 1
            else:
                report.still_unresponsive += 1

        except Exception as exc:
            logger.warning("Closure check failed for %s: %s", store.name, exc)
            report.errors += 1
            report.error_details.append(f"{store.name}: {exc}")

    logger.info("%s", report)
    return report
