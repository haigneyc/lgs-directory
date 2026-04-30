"""Generate a state-level OCS report for store coverage cleanup.

OCS means "Ongoing Coverage Sweep" in the SEO/data-quality runbook. The
report is read-only: it summarizes a state's current store rows, evidence
signals, and suggested next actions without calling external APIs.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import text

from lgs_directory.db import get_session

PUBLIC_STATUSES = {"active", "verified", "candidate"}
TRUSTED_SOURCES = {
    "wpn",
    "games_workshop",
    "comicbookstores",
    "league_comic_geeks",
    "video_game_sage",
    "manual",
}


def _has_text(value: object) -> bool:
    """Return true when value is a non-empty string."""
    return isinstance(value, str) and len(value.strip()) > 0


def classify_row(row: dict[str, object]) -> tuple[str, str]:
    """Classify one store row into an OCS action bucket."""
    status = str(row["status"])
    source = str(row["discovery_source"])
    has_wpn = _has_text(row.get("wpn_id"))
    has_gw = bool(row["has_games_workshop"])
    has_products = bool(row["has_products"])
    has_active_presence = bool(row["has_active_presence"])
    has_phone = _has_text(row.get("phone"))
    trusted_source = source in TRUSTED_SOURCES
    trusted_signal = has_wpn or has_gw or has_products or trusted_source

    if status == "closed":
        return "closed_or_false_positive", "already_closed"
    if status == "unresponsive":
        if trusted_signal:
            return "review_for_reactivation", "suppressed_but_has_trusted_signal"
        if has_active_presence or has_phone:
            return "enrich_then_review", "suppressed_with_contact_signal"
        return "suppressed_pending_evidence", "needs_corroborration"
    if status in PUBLIC_STATUSES and trusted_signal:
        return "public_keep", "trusted_signal"
    if status in PUBLIC_STATUSES and source == "google_places":
        return "suppress_or_enrich", "google_only_public_candidate"
    if status in PUBLIC_STATUSES:
        return "manual_review", "public_without_clear_trust_signal"
    return "manual_review", f"unknown_status:{status}"


def load_rows(state: str, limit: int) -> list[dict[str, object]]:
    """Load store rows and local evidence signals for a state."""
    assert isinstance(state, str) and len(state) == 2, "state must be a two-letter code"
    assert limit > 0, "limit must be positive"
    with get_session() as session:
        result = session.execute(
            text(
                """
                SELECT
                  s.id::text AS id,
                  s.slug,
                  s.name,
                  s.status,
                  s.discovery_source,
                  s.wpn_id,
                  s.google_place_id,
                  s.phone,
                  s.address->>'city' AS city,
                  s.address->>'state' AS state,
                  EXISTS (
                    SELECT 1 FROM store_external_refs r
                    WHERE r.store_id = s.id AND r.provider = 'games_workshop'
                  ) AS has_games_workshop,
                  EXISTS (
                    SELECT 1 FROM store_external_refs r
                    WHERE r.store_id = s.id
                      AND r.provider = 'website_content'
                      AND jsonb_array_length(COALESCE(r.payload->'products', '[]'::jsonb)) > 0
                  ) AS has_products,
                  EXISTS (
                    SELECT 1 FROM online_presences op
                    WHERE op.store_id = s.id AND op.status = 'active'
                  ) AS has_active_presence
                FROM stores s
                WHERE UPPER(s.address->>'state') = :state
                ORDER BY s.status, s.discovery_source, s.name
                LIMIT :limit
                """
            ),
            {"state": state.upper(), "limit": limit},
        ).mappings().all()
    return [dict(row) for row in result]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    """Write detailed rows to CSV."""
    assert len(rows) >= 0, "rows must be a list"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "ocs_action",
        "ocs_reason",
        "id",
        "slug",
        "name",
        "city",
        "state",
        "status",
        "discovery_source",
        "wpn_id",
        "google_place_id",
        "phone",
        "has_games_workshop",
        "has_products",
        "has_active_presence",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            action, reason = classify_row(row)
            writer.writerow({
                "ocs_action": action,
                "ocs_reason": reason,
                **row,
            })


def print_markdown(state: str, rows: list[dict[str, object]], output_csv: Path | None) -> None:
    """Print a markdown state summary."""
    action_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    for row in rows:
        action, _reason = classify_row(row)
        action_counts[action] += 1
        status_counts[str(row["status"])] += 1
        source_counts[str(row["discovery_source"])] += 1

    print(f"# OCS State Report: {state.upper()}")
    print()
    print(f"Total stores: {len(rows)}")
    if output_csv is not None:
        print(f"Detail CSV: `{output_csv}`")
    print()

    print("## Action Buckets")
    for action, count in sorted(action_counts.items()):
        print(f"- `{action}`: {count}")
    print()

    print("## Status Counts")
    for status, count in sorted(status_counts.items()):
        print(f"- `{status}`: {count}")
    print()

    print("## Source Counts")
    for source, count in sorted(source_counts.items()):
        print(f"- `{source}`: {count}")
    print()

    print("## Priority Samples")
    priority_actions = {
        "suppress_or_enrich",
        "review_for_reactivation",
        "enrich_then_review",
        "manual_review",
    }
    samples = [
        row for row in rows
        if classify_row(row)[0] in priority_actions
    ][:20]
    if len(samples) == 0:
        print("- No priority samples.")
        return
    for row in samples:
        action, reason = classify_row(row)
        city = row.get("city") or ""
        print(f"- `{action}` `{reason}`: {row['name']} ({city}, {state.upper()})")


def main() -> None:
    """Run the OCS state report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="Two-letter state code, e.g. TX")
    parser.add_argument("--limit", type=int, default=50_000)
    parser.add_argument("--output-csv", type=Path, default=None)
    args = parser.parse_args()

    state = args.state.upper().strip()
    if len(state) != 2 or not state.isalpha():
        parser.error("--state must be a two-letter state code")

    rows = load_rows(state, args.limit)
    if args.output_csv is not None:
        write_csv(args.output_csv, rows)
    print_markdown(state, rows, args.output_csv)

    if len(rows) == 0:
        print("No rows found for state.", file=sys.stderr)


if __name__ == "__main__":
    main()
