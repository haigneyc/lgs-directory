"""Plan and optionally apply public store SEO cleanup actions.

Reads ``public-store-quality.csv`` from ``audit_public_store_quality.py`` and
turns broad audit buckets into safer operational groups:

* close_high_confidence: obvious false positives, set ``status=closed``.
* suppress_from_public: weak/uncertain rows, set ``status=unresponsive``.
* manual_review: ambiguous rows left untouched.

The default is read-only. Use ``--apply`` to write status changes.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, text

from lgs_directory.db import get_session
from lgs_directory.models.enums import CheckType, StoreStatus
from lgs_directory.models.store import Store
from lgs_directory.models.validation_log import ValidationLog

PUBLIC_STATUSES = {
    StoreStatus.ACTIVE.value,
    StoreStatus.VERIFIED.value,
    StoreStatus.CANDIDATE.value,
}
OUTPUT_FILES = {
    "close_high_confidence": "close-high-confidence.csv",
    "suppress_from_public": "suppress-from-public.csv",
    "manual_review": "manual-review.csv",
    "keep": "keep.csv",
}


HIGH_CONFIDENCE_CLOSE_PATTERNS = (
    re.compile(r"\bgamestop\b", re.IGNORECASE),
    re.compile(r"\bgame\s+stop\b", re.IGNORECASE),
    re.compile(r"\bbarnes\s+&?\s*noble\b", re.IGNORECASE),
    re.compile(r"\bbest\s+buy\b", re.IGNORECASE),
    re.compile(r"\bhobby\s+lobby\b", re.IGNORECASE),
    re.compile(r"\bmichaels\b", re.IGNORECASE),
    re.compile(r"\bwalmart\b", re.IGNORECASE),
    re.compile(r"\btarget\b", re.IGNORECASE),
    re.compile(r"\bacademy\s+sports\b", re.IGNORECASE),
    re.compile(r"\btractor\s+supply\b", re.IGNORECASE),
    re.compile(r"\bdollar\s+(general|tree|store)\b", re.IGNORECASE),
    re.compile(r"\bfamily\s+dollar\b", re.IGNORECASE),
    re.compile(r"\bfive\s+below\b", re.IGNORECASE),
    re.compile(r"\bwalgreens\b", re.IGNORECASE),
    re.compile(r"\bcvs\b", re.IGNORECASE),
    re.compile(r"\bgrocery\b", re.IGNORECASE),
    re.compile(r"\bsupermarket\b", re.IGNORECASE),
    re.compile(r"\bcasino\b", re.IGNORECASE),
    re.compile(r"\bliquor\b", re.IGNORECASE),
    re.compile(r"\bpharmacy\b", re.IGNORECASE),
    re.compile(r"\bgas\s+station\b", re.IGNORECASE),
    re.compile(r"\bpawn\b", re.IGNORECASE),
    re.compile(r"\btobacco\b", re.IGNORECASE),
    re.compile(r"\bvape\b", re.IGNORECASE),
    re.compile(r"\bhemp\b", re.IGNORECASE),
    re.compile(r"\bdispensary\b", re.IGNORECASE),
    re.compile(r"\barmory\b", re.IGNORECASE),
    re.compile(r"\barmoury\b", re.IGNORECASE),
    re.compile(r"\bgun\b", re.IGNORECASE),
    re.compile(r"\bfirearm\b", re.IGNORECASE),
    re.compile(r"\bfitness\b", re.IGNORECASE),
    re.compile(r"\bgym\b", re.IGNORECASE),
    re.compile(r"\bdental\b", re.IGNORECASE),
    re.compile(r"\bmedical\b", re.IGNORECASE),
    re.compile(r"\bveterinar", re.IGNORECASE),
    re.compile(r"\blaundromat\b", re.IGNORECASE),
    re.compile(r"\bauto\s+repair\b", re.IGNORECASE),
    re.compile(r"\bcar\s+wash\b", re.IGNORECASE),
)

PROTECT_REVIEW_PATTERNS = (
    re.compile(r"\bgame", re.IGNORECASE),
    re.compile(r"\bwargames?\b", re.IGNORECASE),
    re.compile(r"\bcomic", re.IGNORECASE),
    re.compile(r"\bhobb(y|ies)\b", re.IGNORECASE),
    re.compile(r"\bcards?\b", re.IGNORECASE),
    re.compile(r"\btcg\b", re.IGNORECASE),
    re.compile(r"\btabletop\b", re.IGNORECASE),
    re.compile(r"\bwarhammer\b", re.IGNORECASE),
    re.compile(r"\bpok[eé]mon\b", re.IGNORECASE),
    re.compile(r"\bmtg\b", re.IGNORECASE),
    re.compile(r"\bminiature", re.IGNORECASE),
    re.compile(r"\bcollect", re.IGNORECASE),
)

CHAIN_CLOSE_PATTERNS = (
    re.compile(r"\bgamestop\b", re.IGNORECASE),
    re.compile(r"\bgame\s+stop\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class PlannedRow:
    """One planned cleanup action."""

    row: dict[str, str]
    plan_action: str
    target_status: str
    plan_reason: str


def _int(value: str) -> int:
    """Parse an integer CSV field."""
    try:
        return int(float(value.replace(",", "").strip() or "0"))
    except ValueError:
        return 0


def _matches(name: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    """Return whether any pattern matches name."""
    return any(pattern.search(name) for pattern in patterns)


def _is_high_confidence_close(row: dict[str, str]) -> bool:
    """Return true for rows safe enough to close without web lookup."""
    name = row["name"]
    if _matches(name, CHAIN_CLOSE_PATTERNS):
        return True
    if row["source"] != "google_places":
        return False
    if _matches(name, PROTECT_REVIEW_PATTERNS):
        return False
    return _matches(name, HIGH_CONFIDENCE_CLOSE_PATTERNS)


def plan_row(row: dict[str, str]) -> PlannedRow:
    """Classify an audit CSV row into an operational action."""
    bucket = row["bucket"]
    reason = row["reason"]

    if bucket == "keep":
        return PlannedRow(row, "keep", row["status"], "trusted_by_audit")

    if bucket == "remove_or_pending_review":
        if reason == "blocked_or_obvious_offtopic_name" and _is_high_confidence_close(row):
            return PlannedRow(
                row,
                "close_high_confidence",
                StoreStatus.CLOSED.value,
                "obvious_non_lgs_name_pattern",
            )
        return PlannedRow(
            row,
            "suppress_from_public",
            StoreStatus.UNRESPONSIVE.value,
            reason,
        )

    if bucket == "suspect_noindex":
        return PlannedRow(
            row,
            "suppress_from_public",
            StoreStatus.UNRESPONSIVE.value,
            reason,
        )

    return PlannedRow(row, "manual_review", row["status"], f"unknown_bucket:{bucket}")


def load_plan(audit_csv: Path) -> list[PlannedRow]:
    """Load and classify the audit CSV."""
    with audit_csv.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        rows = [plan_row(dict(row)) for row in reader]
    rows.sort(key=lambda item: (_int(item.row["gsc_impressions"]), item.row["name"]), reverse=True)
    return rows


def write_outputs(plan: list[PlannedRow], output_dir: Path) -> None:
    """Write per-action CSVs for review."""
    output_dir.mkdir(parents=True, exist_ok=True)
    fields = [
        "plan_action",
        "target_status",
        "plan_reason",
        "bucket",
        "action",
        "reason",
        "gsc_impressions",
        "id",
        "slug",
        "name",
        "status",
        "source",
    ]
    grouped: dict[str, list[PlannedRow]] = {key: [] for key in OUTPUT_FILES}
    for item in plan:
        grouped.setdefault(item.plan_action, []).append(item)

    for action, filename in OUTPUT_FILES.items():
        with (output_dir / filename).open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            for item in grouped.get(action, []):
                writer.writerow({
                    "plan_action": item.plan_action,
                    "target_status": item.target_status,
                    "plan_reason": item.plan_reason,
                    **item.row,
                })


def apply_plan(
    plan: list[PlannedRow],
    max_apply: int,
    only: set[str],
    batch_size: int,
    statement_timeout_ms: int,
) -> Counter[str]:
    """Apply non-keep planned status changes."""
    assert max_apply >= 0, "max_apply must be non-negative"
    assert len(only) > 0, "only must include at least one action"
    assert batch_size > 0, "batch_size must be positive"
    assert statement_timeout_ms > 0, "statement_timeout_ms must be positive"
    changed: Counter[str] = Counter()
    eligible = [
        item for item in plan
        if item.plan_action in {"close_high_confidence", "suppress_from_public"}
        and item.plan_action in only
    ]
    if len(eligible) > max_apply:
        raise RuntimeError(
            f"Refusing to update {len(eligible)} stores with --max-apply={max_apply}. "
            "Raise --max-apply after reviewing the generated CSVs."
        )

    with get_session() as session:
        for start in range(0, len(eligible), batch_size):
            batch = eligible[start:start + batch_size]
            batch_by_id = {UUID(item.row["id"]): item for item in batch}
            batch_counts: Counter[str] = Counter()
            try:
                session.execute(text(f"SET statement_timeout = {statement_timeout_ms}"))
                stores = session.execute(
                    select(Store).where(Store.id.in_(batch_by_id.keys()))
                ).scalars().all()
                seen_ids = {store.id for store in stores}
                batch_counts["missing"] += len(set(batch_by_id) - seen_ids)

                for store in stores:
                    item = batch_by_id[store.id]
                    current = StoreStatus(store.status).value
                    if current not in PUBLIC_STATUSES:
                        batch_counts["already_non_public"] += 1
                        continue
                    if current == item.target_status:
                        batch_counts["unchanged"] += 1
                        continue

                    old_status = current
                    store.status = StoreStatus(item.target_status)
                    note = (
                        "\nSEO cleanup 2026-04: "
                        f"{item.plan_action} ({item.plan_reason}); "
                        f"was {old_status}."
                    )
                    store.notes = (store.notes or "") + note
                    session.add(ValidationLog(
                        store_id=store.id,
                        check_type=CheckType.MANUAL_REVIEW,
                        result={
                            "source": "plan_public_store_cleanup",
                            "audit_bucket": item.row["bucket"],
                            "audit_reason": item.row["reason"],
                            "plan_action": item.plan_action,
                            "plan_reason": item.plan_reason,
                            "transition": f"{old_status} -> {item.target_status}",
                        },
                    ))
                    batch_counts[item.plan_action] += 1
                session.commit()
                changed.update(batch_counts)
                print(
                    f"applied batch {start + 1}-{start + len(batch)} "
                    f"of {len(eligible)}",
                    file=sys.stderr,
                )
            except Exception:
                session.rollback()
                raise
    return changed


def main() -> None:
    """Run the cleanup planner."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-csv", type=Path, default=Path("public-store-quality.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/seo"))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--max-apply", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--statement-timeout-ms", type=int, default=120_000)
    parser.add_argument(
        "--only",
        action="append",
        choices=("close_high_confidence", "suppress_from_public"),
        default=None,
        help="Limit --apply to one action. Repeat to include both.",
    )
    args = parser.parse_args()

    if not args.audit_csv.is_file():
        parser.error(f"audit CSV not found: {args.audit_csv}")

    plan = load_plan(args.audit_csv)
    write_outputs(plan, args.output_dir)

    counts = Counter(item.plan_action for item in plan)
    print("# Cleanup plan", file=sys.stderr)
    for action, count in sorted(counts.items()):
        print(f"{action}: {count}", file=sys.stderr)
    print(f"wrote: {args.output_dir}", file=sys.stderr)

    if args.apply:
        only = set(args.only or ["close_high_confidence", "suppress_from_public"])
        changed = apply_plan(
            plan,
            args.max_apply,
            only,
            args.batch_size,
            args.statement_timeout_ms,
        )
        print("# Applied", file=sys.stderr)
        for action, count in sorted(changed.items()):
            print(f"{action}: {count}", file=sys.stderr)


if __name__ == "__main__":
    main()
