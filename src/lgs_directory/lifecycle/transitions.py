"""Store status state machine — transition rules, evaluation, and application."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from lgs_directory.models.enums import (
    ChannelType,
    CheckType,
    PresenceStatus,
    StoreStatus,
)
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store
from lgs_directory.models.validation_log import ValidationLog

logger = logging.getLogger(__name__)

VALID_TRANSITIONS: dict[StoreStatus, set[StoreStatus]] = {
    StoreStatus.CANDIDATE: {StoreStatus.VERIFIED},
    StoreStatus.VERIFIED: {StoreStatus.ACTIVE, StoreStatus.CLOSED},
    StoreStatus.ACTIVE: {StoreStatus.UNRESPONSIVE, StoreStatus.CLOSED},
    StoreStatus.UNRESPONSIVE: {StoreStatus.ACTIVE, StoreStatus.CLOSED},
}

CONSECUTIVE_FAILURE_THRESHOLD = 3


def can_transition(current: StoreStatus, target: StoreStatus) -> bool:
    """Check whether a status transition is allowed."""
    assert isinstance(current, StoreStatus), "current must be a StoreStatus"
    assert isinstance(target, StoreStatus), "target must be a StoreStatus"

    allowed = VALID_TRANSITIONS.get(current, set())
    return target in allowed


def transition_store(
    store: Store,
    target: StoreStatus,
    session: Session,
    reason: str,
) -> bool:
    """Apply a status transition to a store.

    Validates the transition, updates the store, and creates a MANUAL_REVIEW log.

    Returns:
        True if the transition was applied, False if invalid.
    """
    assert isinstance(store, Store), "store must be a Store"
    assert store.id is not None, "Store must be persisted"
    assert isinstance(target, StoreStatus), "target must be a StoreStatus"
    assert isinstance(reason, str) and len(reason) > 0, "reason must be non-empty"

    current = StoreStatus(store.status)
    if not can_transition(current, target):
        logger.warning(
            "Invalid transition %s → %s for store %s",
            current.value, target.value, store.name,
        )
        return False

    old_status = current.value
    store.status = target
    store.last_validated = datetime.now(tz=UTC)

    log = ValidationLog(
        store_id=store.id,
        check_type=CheckType.MANUAL_REVIEW,
        result={
            "transition": f"{old_status} → {target.value}",
            "reason": reason,
        },
    )
    session.add(log)

    logger.info(
        "Store %s: %s → %s (%s)",
        store.name, old_status, target.value, reason,
    )
    return True


def _has_consecutive_failures(
    presence: OnlinePresence,
    session: Session,
) -> bool:
    """Check if a presence has CONSECUTIVE_FAILURE_THRESHOLD consecutive HTTP_CHECK failures."""
    assert presence.id is not None, "Presence must be persisted"

    stmt = (
        select(ValidationLog.result)
        .where(ValidationLog.presence_id == presence.id)
        .where(ValidationLog.check_type == CheckType.HTTP_CHECK)
        .order_by(ValidationLog.timestamp.desc())
        .limit(CONSECUTIVE_FAILURE_THRESHOLD)
    )
    rows = list(session.execute(stmt).scalars().all())

    if len(rows) < CONSECUTIVE_FAILURE_THRESHOLD:
        return False

    failure_statuses = {PresenceStatus.UNREACHABLE.value, PresenceStatus.DEAD.value}
    return all(
        row.get("status") in failure_statuses
        for row in rows
    )


def evaluate_store_status(
    store: Store,
    session: Session,
) -> StoreStatus | None:
    """Determine if a store should transition to a new status.

    Rules:
      1. candidate → verified: any ValidationLog exists for this store
      2. verified → active: any presence has sells_mtg_singles=True
      3. active → unresponsive: ALL website presences have 3+ consecutive failures
      4. unresponsive → active: any presence has status=ACTIVE

    Returns:
        The target status, or None if no transition is needed.
    """
    assert isinstance(store, Store), "store must be a Store"
    assert store.id is not None, "Store must be persisted"

    current = StoreStatus(store.status)

    # Rule 1: candidate → verified
    if current == StoreStatus.CANDIDATE:
        has_logs = session.execute(
            select(ValidationLog.id)
            .where(ValidationLog.store_id == store.id)
            .limit(1)
        ).first()
        if has_logs is not None:
            return StoreStatus.VERIFIED
        return None

    # Rule 2: verified → active
    if current == StoreStatus.VERIFIED:
        for presence in store.presences:
            if presence.sells_mtg_singles is True:
                return StoreStatus.ACTIVE
        return None

    # Rule 3: active → unresponsive
    if current == StoreStatus.ACTIVE:
        website_presences = [
            p for p in store.presences
            if p.channel_type == ChannelType.WEBSITE
        ]
        if not website_presences:
            return None

        all_failing = all(
            _has_consecutive_failures(p, session)
            for p in website_presences
        )
        if all_failing:
            return StoreStatus.UNRESPONSIVE
        return None

    # Rule 4: unresponsive → active
    if current == StoreStatus.UNRESPONSIVE:
        for presence in store.presences:
            if presence.status == PresenceStatus.ACTIVE:
                return StoreStatus.ACTIVE
        return None

    return None


def apply_status_evaluation(store: Store, session: Session) -> bool:
    """Evaluate and apply a status transition for a store.

    Returns:
        True if a transition was applied, False otherwise.
    """
    assert isinstance(store, Store), "store must be a Store"
    assert store.id is not None, "Store must be persisted"

    target = evaluate_store_status(store, session)
    if target is None:
        return False

    return transition_store(store, target, session, reason="auto-evaluation")
