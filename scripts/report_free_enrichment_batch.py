"""Build a CSV review report from existing free-enrichment JSON dossiers."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from batch_free_enrich_stores import REPORT_FIELDS, classify_action


def row_from_dossier(path: Path, min_confidence: float) -> dict[str, str]:
    """Build one CSV row from a dossier JSON file."""
    assert path.is_file(), "dossier path must be a file"
    assert min_confidence >= 0, "min_confidence must be non-negative"
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    confidence = data.get("confidence")
    products = data.get("products")
    events = data.get("events_next_30_days")
    synthetic = type("DossierLike", (), {})()
    synthetic.confidence = confidence if isinstance(confidence, (int, float)) else 0.0
    synthetic.products = products if isinstance(products, list) else []
    synthetic.has_events = data.get("has_events") is True
    pages_fetched = data.get("pages_fetched")
    synthetic.pages_fetched = pages_fetched if isinstance(pages_fetched, list) else []
    synthetic.events_next_30_days = events if isinstance(events, list) else []
    action = classify_action(synthetic, min_confidence, None)
    address = data.get("address") if isinstance(data.get("address"), dict) else {}
    return {
        "store_id": str(data.get("store_id") or ""),
        "name": str(data.get("store_name") or ""),
        "slug": str(data.get("slug") or ""),
        "status": "",
        "city": str(address.get("city") or ""),
        "state": str(address.get("state") or ""),
        "website": str(data.get("website_url") or ""),
        "confidence": f"{synthetic.confidence:.2f}",
        "recommended_next_step": str(data.get("recommended_next_step") or ""),
        "action": action,
        "products": "|".join(str(product) for product in synthetic.products),
        "has_events": str(synthetic.has_events).lower(),
        "event_url": str(data.get("event_url") or ""),
        "events_next_30_days": str(len(synthetic.events_next_30_days)),
        "phones": "|".join(
            str(phone) for phone in data.get("phones", []) if isinstance(phone, str)
        ),
        "hours_text": "|".join(
            str(hours) for hours in data.get("hours_text", [])[:5] if isinstance(hours, str)
        ),
        "pages_fetched": str(len(synthetic.pages_fetched)),
        "skipped_urls": json.dumps(data.get("skipped_urls", [])[:5], sort_keys=True),
        "error": "",
        "json_path": str(path),
    }


def main() -> None:
    """Run the report builder."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--report-csv", type=Path, required=True)
    parser.add_argument("--min-confidence", type=float, default=0.65)
    args = parser.parse_args()
    if not args.input_dir.is_dir():
        parser.error("--input-dir must be a directory")
    if args.min_confidence < 0 or args.min_confidence > 1:
        parser.error("--min-confidence must be between 0 and 1")

    rows = [
        row_from_dossier(path, args.min_confidence)
        for path in sorted(args.input_dir.glob("*.json"))
    ]
    args.report_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.report_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote: {args.report_csv}")
    print(f"rows: {len(rows)}")


if __name__ == "__main__":
    main()
