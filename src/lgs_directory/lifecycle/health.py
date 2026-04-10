"""Health checks and revalidation — HTTP checks + re-detection for active stores."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from lgs_directory.lifecycle.transitions import apply_status_evaluation
from lgs_directory.models.enums import (
    ChannelType,
    CheckType,
    PresenceStatus,
    StoreStatus,
)
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store
from lgs_directory.models.validation_log import ValidationLog
from lgs_directory.validation.web_presence import check_url

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckReport:
    """Summary of a health check run."""

    total_presences: int = 0
    active: int = 0
    unreachable: int = 0
    dead: int = 0
    transitions: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"Health check complete: {self.total_presences} presences — "
            f"{self.active} active, {self.unreachable} unreachable, "
            f"{self.dead} dead, {self.transitions} transitions, "
            f"{self.errors} errors"
        )


@dataclass
class RevalidationReport:
    """Summary of a revalidation run."""

    total_stores: int = 0
    platforms_cleared: int = 0
    singles_cleared: int = 0
    platforms_detected: int = 0
    singles_detected: int = 0
    transitions: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"Revalidation complete: {self.total_stores} stores — "
            f"{self.platforms_detected} platforms, "
            f"{self.singles_detected} singles, "
            f"{self.transitions} transitions, "
            f"{self.errors} errors"
        )


def run_health_checks(
    session: Session,
    *,
    limit: int = 500,
) -> HealthCheckReport:
    """Run HTTP health checks on active/unresponsive store websites.

    For each website presence, checks URL accessibility, updates presence
    fields, creates ValidationLog entries, and evaluates store transitions.

    Args:
        session: SQLAlchemy session.
        limit: Max presences to check.

    Returns:
        HealthCheckReport with summary counts.
    """
    assert session is not None, "Session must not be None"
    assert limit > 0, "Limit must be positive"

    report = HealthCheckReport()

    # Query website presences for active/unresponsive stores
    stmt = (
        select(OnlinePresence)
        .join(Store)
        .where(Store.status.in_([StoreStatus.ACTIVE, StoreStatus.UNRESPONSIVE]))
        .where(OnlinePresence.channel_type == ChannelType.WEBSITE)
        .options(joinedload(OnlinePresence.store))
        .limit(limit)
    )
    presences = list(session.execute(stmt).scalars().unique().all())
    assert isinstance(presences, list)

    report.total_presences = len(presences)
    logger.info("Running health checks on %d presences", len(presences))

    # Track stores we've already evaluated to avoid duplicate evaluations
    evaluated_store_ids: set = set()

    now = datetime.now(tz=UTC)

    for presence in presences:
        assert isinstance(presence, OnlinePresence)
        assert presence.url is not None

        try:
            status, http_code, error_msg = check_url(presence.url)

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
                store_id=presence.store_id,
                presence_id=presence.id,
                check_type=CheckType.HTTP_CHECK,
                result=result_data,
            )
            session.add(log)

            # Count results
            if status == PresenceStatus.ACTIVE:
                report.active += 1
            elif status == PresenceStatus.UNREACHABLE:
                report.unreachable += 1
            elif status == PresenceStatus.DEAD:
                report.dead += 1

            logger.info(
                "  %s → %s (HTTP %s)",
                presence.url, status.value, http_code or "N/A",
            )

            # Evaluate store transitions (once per store)
            store = presence.store
            if store.id not in evaluated_store_ids:
                evaluated_store_ids.add(store.id)
                if apply_status_evaluation(store, session):
                    report.transitions += 1

        except Exception as exc:
            logger.warning("Health check failed for %s: %s", presence.url, exc)
            report.errors += 1
            report.error_details.append(f"{presence.url}: {exc}")

    logger.info("%s", report)
    return report


def run_full_revalidation(
    session: Session,
    *,
    limit: int = 200,
    anthropic_api_key: str | None = None,
    llm_budget_cents: int = 500,
) -> RevalidationReport:
    """Re-run platform and singles detection on active/verified stores.

    Clears existing platform and sells_mtg_singles, then re-detects.
    Evaluates store transitions after re-detection.

    Args:
        session: SQLAlchemy session.
        limit: Max stores to process.
        anthropic_api_key: For LLM-based singles detection.
        llm_budget_cents: Max LLM spend for this run.

    Returns:
        RevalidationReport with summary counts.
    """
    assert session is not None, "Session must not be None"
    assert limit > 0, "Limit must be positive"

    from lgs_directory.validation.platform_detect import detect_and_log_platform
    from lgs_directory.validation.singles_detect import detect_singles

    report = RevalidationReport()
    budget_remaining = llm_budget_cents

    # Query active/verified stores
    stmt = (
        select(Store)
        .where(Store.status.in_([StoreStatus.ACTIVE, StoreStatus.VERIFIED]))
        .options(joinedload(Store.presences))
        .limit(limit)
    )
    stores = list(session.execute(stmt).scalars().unique().all())
    assert isinstance(stores, list)

    report.total_stores = len(stores)
    logger.info("Revalidating %d stores", len(stores))

    for store in stores:
        assert isinstance(store, Store)

        try:
            for presence in store.presences:
                if presence.status != PresenceStatus.ACTIVE:
                    continue

                # Clear and re-detect platform
                if presence.platform is not None:
                    presence.platform = None
                    report.platforms_cleared += 1

                try:
                    detect_and_log_platform(presence, session)
                    report.platforms_detected += 1
                except Exception as exc:
                    logger.warning("Platform re-detect failed for %s: %s", presence.url, exc)
                    report.errors += 1
                    report.error_details.append(f"Platform: {presence.url}: {exc}")

                # Clear and re-detect singles
                if presence.sells_mtg_singles is not None:
                    presence.sells_mtg_singles = None
                    report.singles_cleared += 1

                try:
                    result = detect_singles(
                        url=presence.url,
                        platform=presence.platform,
                        anthropic_api_key=anthropic_api_key,
                        budget_remaining_cents=budget_remaining,
                    )
                    presence.sells_mtg_singles = result.sells_mtg_singles
                    if result.estimated_inventory_size is not None:
                        presence.estimated_inventory_size = result.estimated_inventory_size

                    if result.sells_mtg_singles:
                        report.singles_detected += 1

                    if result.method == "llm":
                        budget_remaining = max(0, budget_remaining - 5)

                except Exception as exc:
                    logger.warning("Singles re-detect failed for %s: %s", presence.url, exc)
                    report.errors += 1
                    report.error_details.append(f"Singles: {presence.url}: {exc}")

            # Evaluate store transitions after revalidation
            if apply_status_evaluation(store, session):
                report.transitions += 1

        except Exception as exc:
            logger.warning("Revalidation failed for %s: %s", store.name, exc)
            report.errors += 1
            report.error_details.append(f"Store {store.name}: {exc}")

    logger.info("%s", report)
    return report
