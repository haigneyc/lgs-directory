"""Batch free/public enrichment for stores in one state.

The script is conservative by default: it writes one JSON dossier per store and
a CSV review report, but does not persist anything unless ``--apply`` is set.
When applying, only rows with enough confidence and product evidence are
persisted as ``store_external_refs.provider = 'website_content'``.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from free_enrich_one_store import (
    EnrichmentDossier,
    _choose_presence,
    apply_dossier,
    build_dossier,
)
from sqlalchemy import select

from lgs_directory.db import get_session
from lgs_directory.models.enums import ChannelType, PresenceStatus
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store
from lgs_directory.models.store_external_ref import StoreExternalRef

DEFAULT_EXCLUDED_HOSTS = (
    "facebook.com",
    "instagram.com",
    "m.facebook.com",
    "wpn.wizards.com",
    "warhammer.com",
)

REPORT_FIELDS = (
    "store_id",
    "name",
    "slug",
    "status",
    "city",
    "state",
    "website",
    "confidence",
    "recommended_next_step",
    "action",
    "products",
    "has_events",
    "event_url",
    "events_next_30_days",
    "phones",
    "hours_text",
    "pages_fetched",
    "skipped_urls",
    "error",
    "json_path",
)


def host_for_url(url: str) -> str:
    """Return normalized hostname for a URL."""
    console_url = url if "://" in url else f"https://{url}"
    parsed = urlparse(console_url)
    host = parsed.hostname or ""
    return host.lower().removeprefix("www.")


def is_excluded_url(url: str, excluded_hosts: tuple[str, ...]) -> bool:
    """Return whether URL belongs to an excluded host."""
    host = host_for_url(url)
    return any(host == excluded or host.endswith(f".{excluded}") for excluded in excluded_hosts)


def output_name(store: Store) -> str:
    """Return stable JSON filename for a store."""
    base = store.slug or str(store.id)
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", base).strip("-") + ".json"


def load_google_payload(store_id: Any) -> dict[str, Any] | None:
    """Load Google Places payload for one store."""
    with get_session() as session:
        payload = session.execute(
            select(StoreExternalRef.payload).where(
                StoreExternalRef.store_id == store_id,
                StoreExternalRef.provider == "google_places",
            )
        ).scalar_one_or_none()
    return payload if isinstance(payload, dict) else None


def already_has_content(store_id: Any) -> bool:
    """Return whether the store already has website_content evidence."""
    with get_session() as session:
        existing = session.execute(
            select(StoreExternalRef.id).where(
                StoreExternalRef.store_id == store_id,
                StoreExternalRef.provider == "website_content",
            )
        ).scalar_one_or_none()
    return existing is not None


def candidate_stores(
    state: str,
    limit: int,
    include_existing: bool,
    excluded_hosts: tuple[str, ...],
) -> list[tuple[Store, list[OnlinePresence]]]:
    """Load stores with an active website presence for a state."""
    assert len(state) == 2, "state must be a two-letter code"
    assert limit > 0, "limit must be positive"

    candidates: list[tuple[Store, list[OnlinePresence]]] = []
    seen: set[str] = set()
    with get_session() as session:
        stores = session.execute(
            select(Store)
            .join(OnlinePresence, OnlinePresence.store_id == Store.id)
            .where(
                Store.address["state"].astext == state,
                OnlinePresence.channel_type == ChannelType.WEBSITE,
                OnlinePresence.status == PresenceStatus.ACTIVE,
                Store.status.in_(["active", "verified", "candidate", "unresponsive"]),
            )
            .order_by(Store.status.desc(), Store.name.asc())
            .limit(limit * 5)
        ).scalars().all()

        for store in stores:
            store_id = str(store.id)
            if store_id in seen:
                continue
            seen.add(store_id)
            presences = list(session.execute(
                select(OnlinePresence).where(OnlinePresence.store_id == store.id)
            ).scalars().all())
            try:
                presence = _choose_presence(store, presences)
            except RuntimeError:
                continue
            if is_excluded_url(presence.url, excluded_hosts):
                continue
            if not include_existing and already_has_content(store.id):
                continue
            candidates.append((store, presences))
            if len(candidates) >= limit:
                break
    return candidates


def classify_action(
    dossier: EnrichmentDossier | None,
    min_confidence: float,
    error: str | None,
) -> str:
    """Classify the review/apply action for one result."""
    assert min_confidence >= 0, "min_confidence must be non-negative"
    assert min_confidence <= 1, "min_confidence must not exceed one"
    if error is not None:
        return "retry_or_debug"
    if dossier is None:
        return "retry_or_debug"
    if dossier.confidence >= min_confidence and len(dossier.products) > 0:
        return "auto_apply"
    if len(dossier.pages_fetched) == 0:
        return "retry_or_debug"
    if len(dossier.products) == 0 and not dossier.has_events:
        return "not_lgs_or_manual_review"
    return "manual_review"


def row_for_result(
    store: Store,
    dossier: EnrichmentDossier | None,
    action: str,
    json_path: Path,
    error: str | None,
) -> dict[str, str]:
    """Build one CSV row from a batch result."""
    assert isinstance(action, str) and len(action) > 0, "action must be non-empty"
    assert json_path.suffix == ".json", "json_path must point to a JSON file"
    address = store.address or {}
    if dossier is None:
        return {
            "store_id": str(store.id),
            "name": store.name,
            "slug": store.slug or "",
            "status": store.status,
            "city": str(address.get("city") or ""),
            "state": str(address.get("state") or ""),
            "website": "",
            "confidence": "",
            "recommended_next_step": "",
            "action": action,
            "products": "",
            "has_events": "",
            "event_url": "",
            "events_next_30_days": "",
            "phones": "",
            "hours_text": "",
            "pages_fetched": "",
            "skipped_urls": "",
            "error": error or "",
            "json_path": str(json_path),
        }
    return {
        "store_id": dossier.store_id,
        "name": dossier.store_name,
        "slug": dossier.slug or "",
        "status": store.status,
        "city": str(address.get("city") or ""),
        "state": str(address.get("state") or ""),
        "website": dossier.website_url,
        "confidence": f"{dossier.confidence:.2f}",
        "recommended_next_step": dossier.recommended_next_step,
        "action": action,
        "products": "|".join(dossier.products),
        "has_events": str(dossier.has_events).lower(),
        "event_url": dossier.event_url or "",
        "events_next_30_days": str(len(dossier.events_next_30_days)),
        "phones": "|".join(dossier.phones),
        "hours_text": "|".join(dossier.hours_text[:5]),
        "pages_fetched": str(len(dossier.pages_fetched)),
        "skipped_urls": json.dumps(dossier.skipped_urls[:5], sort_keys=True),
        "error": error or "",
        "json_path": str(json_path),
    }


def write_report(rows: list[dict[str, str]], report_path: Path) -> None:
    """Write CSV report rows."""
    assert report_path.suffix == ".csv", "report_path must be a CSV path"
    assert isinstance(rows, list), "rows must be a list"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def enrich_one(
    store: Store,
    presences: list[OnlinePresence],
    output_dir: Path,
) -> tuple[EnrichmentDossier | None, Path, str | None]:
    """Build and write one store dossier."""
    assert output_dir.is_dir(), "output_dir must exist"
    assert isinstance(presences, list), "presences must be a list"
    json_path = output_dir / output_name(store)
    try:
        presence = _choose_presence(store, presences)
        google_payload = load_google_payload(store.id)
        dossier = build_dossier(store, presence, google_payload)
        json_path.write_text(
            json.dumps(asdict(dossier), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return dossier, json_path, None
    except Exception as exc:  # noqa: BLE001 - batch report must keep going.
        return None, json_path, f"{type(exc).__name__}: {exc}"


def parse_args() -> argparse.Namespace:
    """Parse CLI args."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="Two-letter state code, e.g. TX")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--output-dir", type=Path, default=Path("data/enrichment/batch"))
    parser.add_argument("--report-csv", type=Path, default=None)
    parser.add_argument("--min-confidence", type=float, default=0.65)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--include-existing", action="store_true")
    parser.add_argument(
        "--include-excluded-hosts",
        action="store_true",
        help="Include Facebook, WPN placeholders, and corporate Warhammer URLs.",
    )
    args = parser.parse_args()
    state = args.state.upper().strip()
    if len(state) != 2 or not state.isalpha():
        parser.error("--state must be a two-letter state code")
    if args.limit <= 0:
        parser.error("--limit must be positive")
    if args.min_confidence < 0 or args.min_confidence > 1:
        parser.error("--min-confidence must be between 0 and 1")
    args.state = state
    return args


def main() -> None:
    """Run the batch enrichment workflow."""
    args = parse_args()
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.report_csv or (output_dir / f"{args.state.lower()}-enrichment-report.csv")
    excluded_hosts = () if args.include_excluded_hosts else DEFAULT_EXCLUDED_HOSTS
    candidates = candidate_stores(
        args.state,
        args.limit,
        args.include_existing,
        excluded_hosts,
    )

    rows: list[dict[str, str]] = []
    applied = 0
    for index, (store, presences) in enumerate(candidates, start=1):
        print(f"[{index}/{len(candidates)}] {store.name}", file=sys.stderr)
        dossier, json_path, error = enrich_one(store, presences, output_dir)
        action = classify_action(dossier, args.min_confidence, error)
        if args.apply and action == "auto_apply" and dossier is not None:
            apply_dossier(dossier)
            applied += 1
        rows.append(row_for_result(store, dossier, action, json_path, error))

    write_report(rows, report_path)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["action"]] = counts.get(row["action"], 0) + 1

    print("# Batch enrichment")
    print(f"state: {args.state}")
    print(f"candidates: {len(candidates)}")
    print(f"applied: {applied}")
    for action, count in sorted(counts.items()):
        print(f"{action}: {count}")
    print(f"report: {report_path}")
    print(f"json_dir: {output_dir}")


if __name__ == "__main__":
    main()
