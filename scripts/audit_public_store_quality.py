"""Read-only public store quality audit for SEO recovery.

Buckets public inventory into:
  * keep
  * suspect_noindex
  * remove_or_pending_review

Uses only local database/content signals. It never calls Google Places.
Optional GSC pages CSV input can prioritize high-impression UUID URLs.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import text

from lgs_directory.db import get_session
from lgs_directory.discovery.quality_filters import is_name_blocked

PUBLIC_STATUSES = ("active", "verified", "candidate")
MAX_ROWS = 100_000
MAX_SAMPLE = 20
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
OBVIOUS_NON_LGS_PATTERNS = (
    re.compile(r"\b(college|university|campus)\s+bookstore\b", re.IGNORECASE),
    re.compile(r"\bbookstore\b", re.IGNORECASE),
    re.compile(r"\bgamestop\b", re.IGNORECASE),
    re.compile(r"\bgame\s+stop\b", re.IGNORECASE),
)


def _page_column(row: dict[str, str]) -> str | None:
    """Return the likely URL column from a GSC CSV row."""
    for key in ("Page", "Top pages", "URL", "Url", "page", "url"):
        value = row.get(key)
        if value:
            return value
    return None


def _int_column(row: dict[str, str], key: str) -> int:
    """Parse a possibly formatted integer column from GSC CSV."""
    raw = row.get(key, "0").replace(",", "").strip()
    if len(raw) == 0:
        return 0
    try:
        return int(float(raw))
    except ValueError:
        return 0


def load_gsc_priorities(path: Path | None) -> dict[str, int]:
    """Load impressions by store URL token from an optional GSC pages CSV."""
    assert path is None or isinstance(path, Path), "path must be Path or None"
    if path is None:
        return {}

    priorities: dict[str, int] = {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for idx, row in enumerate(reader):
            if idx >= MAX_ROWS:
                break
            page = _page_column(row)
            if page is None:
                continue
            parsed = urlparse(page)
            url_path = parsed.path if parsed.scheme else page
            parts = [part for part in url_path.split("/") if part]
            if len(parts) >= 2 and parts[0] == "store":
                priorities[parts[1]] = _int_column(row, "Impressions")
    return priorities


def _matches_any(name: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    """Return true if any bounded audit pattern matches a store name."""
    assert isinstance(name, str), "name must be a string"
    limit = min(len(patterns), 20)
    return any(patterns[idx].search(name) for idx in range(limit))


def bucket_row(row: dict[str, object], priorities: dict[str, int]) -> tuple[str, str, str]:
    """Bucket one store row from local deterministic signals."""
    assert isinstance(row, dict), "row must be a dict"
    assert isinstance(priorities, dict), "priorities must be a dict"

    name = str(row["name"])
    slug = row.get("slug")
    source = str(row["discovery_source"])
    has_wpn = row["wpn_id"] is not None
    has_games_workshop = bool(row["has_games_workshop"])
    has_products = bool(row["has_products"])
    has_active_presence = bool(row["has_active_presence"])

    token = str(slug or row["id"])
    impressions = priorities.get(token, 0)
    if slug is None or str(slug).strip() == "":
        return "suspect_noindex", "slugless_public_store", "noindex"
    if is_name_blocked(name) or _matches_any(name, OBVIOUS_NON_LGS_PATTERNS):
        return "remove_or_pending_review", "blocked_or_obvious_offtopic_name", "manual_review"
    if has_wpn or has_games_workshop or has_products:
        return "keep", "trusted_local_signal", "keep"
    if source == "google_places" and not has_active_presence:
        return "remove_or_pending_review", "google_only_no_active_presence", "manual_review"
    if source == "google_places" or impressions > 0:
        return "suspect_noindex", "weak_google_or_gsc_signal", "noindex"
    return "keep", "no_negative_signal", "keep"


def main() -> None:
    """Run the audit and write CSV rows to stdout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gsc-pages-csv", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=MAX_ROWS)
    args = parser.parse_args()
    assert args.limit > 0, "limit must be positive"
    if args.gsc_pages_csv is not None and not args.gsc_pages_csv.is_file():
        parser.error(
            f"CSV file not found: {args.gsc_pages_csv}. "
            "Pass the actual Performance > Search results > Pages export path."
        )
    limit = min(args.limit, MAX_ROWS)

    priorities = load_gsc_priorities(args.gsc_pages_csv)

    with get_session() as session:
        rows = session.execute(
            text(
                """
                SELECT
                  s.id::text AS id,
                  s.slug,
                  s.name,
                  s.status,
                  s.discovery_source,
                  s.wpn_id,
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
                WHERE s.status = ANY(:statuses)
                ORDER BY s.status, s.discovery_source, s.name
                LIMIT :limit
                """
            ),
            {"statuses": list(PUBLIC_STATUSES), "limit": limit},
        ).mappings().all()

    writer = csv.writer(sys.stdout)
    writer.writerow([
        "bucket", "action", "reason", "gsc_impressions", "id", "slug",
        "name", "status", "source",
    ])
    counts: dict[str, int] = {}
    for raw in rows:
        row = dict(raw)
        bucket, reason, action = bucket_row(row, priorities)
        token = str(row.get("slug") or row["id"])
        counts[bucket] = counts.get(bucket, 0) + 1
        writer.writerow([
            bucket,
            action,
            reason,
            priorities.get(token, 0),
            row["id"],
            row.get("slug") or "",
            row["name"],
            row["status"],
            row["discovery_source"],
        ])

    print("\n# Summary", file=sys.stderr)
    for bucket, count in sorted(counts.items()):
        print(f"{bucket}: {count}", file=sys.stderr)


if __name__ == "__main__":
    main()
