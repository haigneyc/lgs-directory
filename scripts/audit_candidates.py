#!/usr/bin/env python3
"""Audit existing candidate stores for suspected false positives.

Scans all stores with status='candidate' and checks:
  1. Name against the quality-filter blocklist
  2. Content scraper results (if available) for 0 products + low confidence

Outputs a report of suspected false positives for manual review.
Does NOT auto-reject any stores.

Usage:
    python scripts/audit_candidates.py [--verbose] [--output report.csv]
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path

import click
from sqlalchemy import select
from sqlalchemy.orm import Session

from lgs_directory.db import get_session
from lgs_directory.discovery.quality_filters import (
    check_content_confidence,
    is_name_blocked,
)
from lgs_directory.models.enums import CheckType, StoreStatus
from lgs_directory.models.store import Store
from lgs_directory.models.validation_log import ValidationLog

# Safety cap for query results
_MAX_CANDIDATES = 50_000
_MAX_VALIDATION_LOGS = 200_000


@dataclass(frozen=True)
class FlaggedStore:
    """A candidate store flagged as a suspected false positive."""

    store_id: str
    name: str
    city: str
    state: str
    reasons: list[str]


@dataclass
class AuditReport:
    """Summary of the candidate audit."""

    total_candidates: int = 0
    name_blocked: int = 0
    low_content_confidence: int = 0
    flagged_stores: list[FlaggedStore] = field(default_factory=list)


def _get_content_extract_for_store(
    store_id: str,
    session: Session,
) -> dict | None:
    """Retrieve the most recent content_extract validation log for a store.

    Returns the result JSONB dict, or None if no content extraction exists.
    """
    assert isinstance(store_id, str), "store_id must be a string"
    assert session is not None, "session must not be None"

    stmt = (
        select(ValidationLog)
        .where(ValidationLog.store_id == store_id)
        .where(ValidationLog.check_type == CheckType.CONTENT_EXTRACT)
        .order_by(ValidationLog.timestamp.desc())
        .limit(1)
    )
    log = session.execute(stmt).scalar_one_or_none()

    if log is None:
        return None

    assert isinstance(log.result, dict), "validation log result must be a dict"
    return log.result


def run_audit(session: Session) -> AuditReport:
    """Run the full candidate audit and return the report.

    Does NOT modify any data.
    """
    assert session is not None, "session must not be None"

    report = AuditReport()

    # Load all candidate stores
    stmt = (
        select(Store)
        .where(Store.status == StoreStatus.CANDIDATE)
        .limit(_MAX_CANDIDATES)
    )
    candidates = list(session.execute(stmt).scalars().all())
    report.total_candidates = len(candidates)
    assert isinstance(candidates, list), "candidates must be a list"

    for store in candidates:
        assert isinstance(store, Store), "each result must be a Store"

        reasons: list[str] = []

        # Check 1: Name blocklist
        if is_name_blocked(store.name):
            reasons.append(f"name_blocked: '{store.name}'")
            report.name_blocked += 1

        # Check 2: Content scraper confidence
        content_result = _get_content_extract_for_store(str(store.id), session)
        if content_result is not None:
            products = content_result.get("products", [])
            confidence = content_result.get("confidence", 1.0)

            # Ensure confidence is a float for the gate check.
            # JSONB may return non-numeric strings; skip the check if so.
            if not isinstance(confidence, float):
                try:
                    confidence = float(confidence)
                except (ValueError, TypeError):
                    continue

            gate = check_content_confidence(products, confidence)
            if gate.should_reject:
                reasons.append(f"low_content_confidence: {gate.reason}")
                report.low_content_confidence += 1

        if len(reasons) > 0:
            address = store.address if isinstance(store.address, dict) else {}
            flagged = FlaggedStore(
                store_id=str(store.id),
                name=store.name,
                city=address.get("city", ""),
                state=address.get("state", ""),
                reasons=reasons,
            )
            report.flagged_stores.append(flagged)

    return report


def _print_report(report: AuditReport) -> None:
    """Print audit report to stdout."""
    assert isinstance(report, AuditReport), "report must be an AuditReport"

    click.echo("\n=== Candidate Audit Report ===")
    click.echo(f"Total candidates scanned:        {report.total_candidates}")
    click.echo(f"Flagged by name blocklist:        {report.name_blocked}")
    click.echo(f"Flagged by low content confidence: {report.low_content_confidence}")
    click.echo(f"Total suspected false positives:  {len(report.flagged_stores)}")

    if len(report.flagged_stores) == 0:
        click.echo("\nNo suspected false positives found.")
        return

    click.echo("\n--- Suspected False Positives ---")
    for i, flagged in enumerate(report.flagged_stores):
        if i >= 500:  # Safety cap on output
            click.echo(f"... and {len(report.flagged_stores) - 500} more")
            break
        click.echo(
            f"\n  [{i + 1}] {flagged.name}"
            f"\n      ID:      {flagged.store_id}"
            f"\n      City:    {flagged.city}, {flagged.state}"
            f"\n      Reasons: {'; '.join(flagged.reasons)}"
        )


def _write_csv(report: AuditReport, output_path: Path) -> None:
    """Write flagged stores to a CSV file."""
    assert isinstance(output_path, Path), "output_path must be a Path"
    assert isinstance(report, AuditReport), "report must be an AuditReport"

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["store_id", "name", "city", "state", "reasons"])
        for flagged in report.flagged_stores:
            writer.writerow([
                flagged.store_id,
                flagged.name,
                flagged.city,
                flagged.state,
                "; ".join(flagged.reasons),
            ])

    click.echo(f"\nCSV report written to: {output_path}")


@click.command()
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose output.")
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Write flagged stores to a CSV file.",
)
def main(verbose: bool, output: Path | None) -> None:
    """Audit candidate stores for suspected false positives."""
    assert isinstance(verbose, bool), "verbose must be a bool"

    if verbose:
        import logging
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    with get_session() as session:
        report = run_audit(session)
        # Roll back since we didn't modify anything
        session.rollback()

    _print_report(report)

    if output is not None:
        _write_csv(report, output)

    # Exit with code 1 if false positives were found (useful for CI)
    if len(report.flagged_stores) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
