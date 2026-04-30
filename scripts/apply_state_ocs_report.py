"""Apply selected actions from a state OCS report CSV.

The default is a dry run. This script is intentionally narrow: it only
supports suppressing rows from public/indexable status by moving them to
``unresponsive``. It does not close stores.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from lgs_directory.db import get_session
from lgs_directory.models.enums import CheckType, StoreStatus
from lgs_directory.models.store import Store
from lgs_directory.models.validation_log import ValidationLog

PUBLIC_STATUSES = {
    StoreStatus.ACTIVE.value,
    StoreStatus.VERIFIED.value,
    StoreStatus.CANDIDATE.value,
}
DEFAULT_ACTIONS = {"suppress_or_enrich"}


def load_target_ids(path: Path, actions: set[str]) -> list[UUID]:
    """Load target store IDs from a state OCS CSV."""
    assert path.is_file(), "state OCS CSV must exist"
    assert len(actions) > 0, "actions must not be empty"
    target_ids: list[UUID] = []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get("ocs_action") in actions:
                target_ids.append(UUID(str(row["id"])))
    return target_ids


def apply_suppression(ids: list[UUID], dry_run: bool, max_apply: int) -> Counter[str]:
    """Move selected public rows to unresponsive."""
    assert max_apply >= 0, "max_apply must be non-negative"
    if not dry_run and len(ids) > max_apply:
        raise RuntimeError(
            f"Refusing to update {len(ids)} stores with --max-apply={max_apply}."
        )

    counts: Counter[str] = Counter()
    with get_session() as session:
        stores = session.execute(
            select(Store).where(Store.id.in_(ids))
        ).scalars().all()
        found_ids = {store.id for store in stores}
        counts["missing"] += len(set(ids) - found_ids)

        for store in stores:
            current = StoreStatus(store.status).value
            if current not in PUBLIC_STATUSES:
                counts["already_non_public"] += 1
                continue
            if dry_run:
                counts["would_suppress"] += 1
                continue

            store.status = StoreStatus.UNRESPONSIVE
            store.notes = (
                (store.notes or "")
                + f"\nOCS cleanup 2026-04: suppressed from public; was {current}."
            )
            session.add(ValidationLog(
                store_id=store.id,
                check_type=CheckType.MANUAL_REVIEW,
                result={
                    "source": "apply_state_ocs_report",
                    "action": "suppress_from_public",
                    "transition": f"{current} -> {StoreStatus.UNRESPONSIVE.value}",
                },
            ))
            counts["suppressed"] += 1

        if dry_run:
            session.rollback()
        else:
            session.commit()

    return counts


def main() -> None:
    """Run the state OCS apply helper."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument(
        "--action",
        action="append",
        default=None,
        help="OCS action to apply. Defaults to suppress_or_enrich.",
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--max-apply", type=int, default=0)
    args = parser.parse_args()

    actions = set(args.action or DEFAULT_ACTIONS)
    target_ids = load_target_ids(args.csv, actions)
    print(f"targets: {len(target_ids)}", file=sys.stderr)
    counts = apply_suppression(target_ids, not args.apply, args.max_apply)
    for key, count in sorted(counts.items()):
        print(f"{key}: {count}", file=sys.stderr)


if __name__ == "__main__":
    main()
