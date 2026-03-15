"""Validation orchestrator — runs presence → platform → singles pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from lgs_directory.models.enums import PresenceStatus
from lgs_directory.models.store import Store
from lgs_directory.validation.platform_detect import detect_and_log_platform
from lgs_directory.validation.singles_detect import detect_singles
from lgs_directory.validation.web_presence import detect_web_presence

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """Summary of a full validation run."""

    total_stores: int = 0
    presences_found: int = 0
    platforms_detected: int = 0
    singles_detected: int = 0
    llm_calls: int = 0
    llm_spend_cents: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"Validation complete: {self.total_stores} stores — "
            f"{self.presences_found} presences, "
            f"{self.platforms_detected} platforms, "
            f"{self.singles_detected} singles, "
            f"{self.errors} errors"
        )


def validate_stores(
    session: Session,
    *,
    status_filter: str = "candidate",
    limit: int = 100,
    dry_run: bool = False,
    anthropic_api_key: str | None = None,
    llm_budget_cents: int = 500,
) -> ValidationReport:
    """Run the full validation pipeline on matching stores.

    Pipeline per store:
      1. Web presence check (validate URLs)
      2. Platform detection (identify e-commerce platform)
      3. Singles detection (check for MTG singles)

    Args:
        session: SQLAlchemy session.
        status_filter: Only validate stores with this status.
        limit: Max stores to process.
        dry_run: If True, report what would be done without changes.
        anthropic_api_key: For LLM-based singles detection.
        llm_budget_cents: Max LLM spend for this run.

    Returns:
        ValidationReport with summary counts.
    """
    assert session is not None, "Session must not be None"
    assert limit > 0, "Limit must be positive"

    report = ValidationReport()
    budget_remaining = llm_budget_cents

    # Query stores
    stmt = (
        select(Store)
        .where(Store.status == status_filter)
        .limit(limit)
    )
    stores = list(session.execute(stmt).scalars().all())
    report.total_stores = len(stores)
    assert isinstance(stores, list)

    logger.info("Validating %d stores (status=%s)", len(stores), status_filter)

    if dry_run:
        logger.info("Dry run — no changes will be made")
        return report

    for i, store in enumerate(stores):
        assert isinstance(store, Store)
        logger.info(
            "[%d/%d] Validating: %s",
            i + 1, report.total_stores, store.name,
        )

        try:
            # Step 1: Web presence
            updated_presences = detect_web_presence(store, session)
            report.presences_found += len(updated_presences)

            # Step 2: Platform detection (on active presences)
            for presence in updated_presences:
                if presence.status != PresenceStatus.ACTIVE:
                    continue

                if presence.platform is not None:
                    continue

                try:
                    detect_and_log_platform(presence, session)
                    report.platforms_detected += 1
                except Exception as exc:
                    logger.warning("Platform detection failed for %s: %s", presence.url, exc)
                    report.errors += 1
                    report.error_details.append(f"Platform: {presence.url}: {exc}")

            # Step 3: Singles detection (on active presences)
            for presence in updated_presences:
                if presence.status != PresenceStatus.ACTIVE:
                    continue

                if presence.sells_mtg_singles is not None:
                    continue

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
                        report.llm_calls += 1
                        llm_cost = 5  # ~5 cents per Haiku call
                        report.llm_spend_cents += llm_cost
                        budget_remaining = max(0, budget_remaining - llm_cost)

                except Exception as exc:
                    logger.warning("Singles detection failed for %s: %s", presence.url, exc)
                    report.errors += 1
                    report.error_details.append(f"Singles: {presence.url}: {exc}")

        except Exception as exc:
            logger.warning("Store validation failed for %s: %s", store.name, exc)
            report.errors += 1
            report.error_details.append(f"Store {store.name}: {exc}")

    logger.info("%s", report)
    return report
