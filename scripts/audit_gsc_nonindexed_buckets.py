"""Bucket GSC non-indexed URL exports by Roll For Store URL type.

Input is one or more CSV exports from GSC indexing reports. The script
does not call any API.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from urllib.parse import urlparse

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
MAX_ROWS = 200_000
MAX_SAMPLES = 8

BUCKET_INFO = {
    "store_uuid": (
        "UUID store URL or slugless public row",
        "redirect/noindex expected",
        "redirect",
    ),
    "store_slug": ("Store detail slug URL", "indexable unless thin/off-topic", "manual_review"),
    "state": ("State directory page", "indexable template", "fix_template"),
    "city": ("City directory page", "indexable when city has stores", "enrich"),
    "category_static": ("Category/static SEO page", "indexable", "fix_template"),
    "guide": ("Guide page", "indexable when published", "enrich"),
    "unknown": ("Unknown URL pattern", "unknown", "manual_review"),
}


def _page_column(row: dict[str, str]) -> str | None:
    """Return the likely URL column from a GSC CSV row."""
    for key in ("Page", "Top pages", "URL", "Url", "page", "url"):
        value = row.get(key)
        if value:
            return value
    return None


def _classify(path: str) -> str:
    """Classify a Roll For Store URL path into an SEO recovery bucket."""
    assert isinstance(path, str), "path must be a string"
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "store":
        return "store_uuid" if UUID_RE.match(parts[1]) else "store_slug"
    if len(parts) == 2 and parts[0] == "stores":
        return "state"
    if len(parts) >= 3 and parts[0] == "stores":
        return "city"
    if len(parts) >= 1 and parts[0] in {
        "comics", "retro-games", "warhammer", "near-me", "stores",
        "affiliate-disclosure", "privacy-policy",
    }:
        return "category_static"
    if len(parts) >= 1 and parts[0] == "guides":
        return "guide"
    return "unknown"


def _action_for(bucket: str, path: str) -> str:
    """Return the expected recovery action for a URL bucket."""
    assert bucket in BUCKET_INFO, "bucket must be known"
    if bucket == "store_uuid":
        return "redirect" if UUID_RE.search(path) else "noindex"
    if bucket == "state":
        return "fix_template"
    if bucket == "city":
        return "enrich"
    return BUCKET_INFO[bucket][2]


def main() -> None:
    """Read GSC CSV exports and print grouped counts/samples."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_paths", nargs="+", type=Path)
    args = parser.parse_args()
    missing_paths = [str(path) for path in args.csv_paths if not path.is_file()]
    if missing_paths:
        parser.error(
            "CSV file not found: "
            + ", ".join(missing_paths)
            + ". Pass the actual GSC export path."
        )

    buckets: dict[str, dict[str, object]] = {}
    for key in BUCKET_INFO:
        buckets[key] = {"count": 0, "samples": []}

    rows_seen = 0
    for csv_path in args.csv_paths:
        with csv_path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if rows_seen >= MAX_ROWS:
                    break
                rows_seen += 1
                page = _page_column(row)
                if page is None:
                    continue
                parsed = urlparse(page)
                path = parsed.path if parsed.scheme else page
                bucket = _classify(path)
                info = buckets[bucket]
                info["count"] = int(info["count"]) + 1
                samples = info["samples"]
                assert isinstance(samples, list), "samples must be a list"
                if len(samples) < MAX_SAMPLES:
                    samples.append(path)

    print("bucket,count,likely_cause,expected_indexability,action,samples")
    for bucket, details in buckets.items():
        count = int(details["count"])
        cause, expected, _ = BUCKET_INFO[bucket]
        samples = details["samples"]
        assert isinstance(samples, list), "samples must be a list"
        action = _action_for(bucket, samples[0] if samples else "")
        sample_text = " | ".join(str(sample) for sample in samples)
        print(f"{bucket},{count},{cause},{expected},{action},{sample_text}")


if __name__ == "__main__":
    main()
