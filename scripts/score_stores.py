#!/usr/bin/env python3
"""Calculate trust scores for all stores and output a CSV report.

Usage:
    python scripts/score_stores.py [--output trust_scores.csv]

Outputs: store_id, name, city, state, trust_score, signals
Sorted by trust_score ascending (lowest trust first).
"""

from __future__ import annotations

import csv

import click
from sqlalchemy import select

from lgs_directory.db import get_session
from lgs_directory.discovery.trust_score import calculate_trust_score
from lgs_directory.models.store import Store
from lgs_directory.models.store_external_ref import StoreExternalRef

# Safety cap on total stores to process
_MAX_STORES = 50_000
_MAX_REFS_PER_STORE = 20


def _get_content_data(
    session: object,
    store_id: object,
) -> tuple[list[str] | None, float | None]:
    """Fetch content scraper data for a store.

    Returns (products, confidence) or (None, None) if no content ref exists.
    """
    assert store_id is not None, "store_id must not be None"

    stmt = (
        select(StoreExternalRef)
        .where(
            StoreExternalRef.store_id == store_id,
            StoreExternalRef.provider == "website_content",
        )
        .limit(1)
    )
    # session is a sqlalchemy Session; using execute on it
    ref = session.execute(stmt).scalar_one_or_none()  # type: ignore[union-attr]

    if ref is None or ref.payload is None:
        return None, None

    payload = ref.payload
    assert isinstance(payload, dict), "payload must be a dict"

    products = payload.get("products", [])
    confidence = payload.get("confidence")

    if not isinstance(products, list):
        products = []

    if confidence is not None:
        confidence = float(confidence)

    return products, confidence


def _has_website(session: object, store_id: object) -> bool:
    """Check if a store has a website URL via online presences or external refs."""
    assert store_id is not None, "store_id must not be None"

    # Check if there's a website_content ref (implies website exists)
    stmt = (
        select(StoreExternalRef.id)
        .where(
            StoreExternalRef.store_id == store_id,
            StoreExternalRef.provider == "website_content",
        )
        .limit(1)
    )
    ref = session.execute(stmt).scalar_one_or_none()  # type: ignore[union-attr]
    return ref is not None


@click.command()
@click.option("--output", "-o", default="trust_scores.csv", help="Output CSV path.")
def main(output: str) -> None:
    """Calculate trust scores for all stores and write CSV."""
    assert isinstance(output, str), "output must be a string"
    assert len(output) > 0, "output must not be empty"

    with get_session() as session:
        stmt = select(Store).order_by(Store.name).limit(_MAX_STORES)
        stores = session.execute(stmt).scalars().all()

        click.echo(f"Scoring {len(stores)} stores...")

        rows: list[dict[str, object]] = []
        for idx, store in enumerate(stores):
            if idx >= _MAX_STORES:
                break

            assert isinstance(store, Store), "must be a Store"

            city = (store.address or {}).get("city", "")
            state = (store.address or {}).get("state", "")

            products, confidence = _get_content_data(session, store.id)
            has_site = _has_website(session, store.id)

            result = calculate_trust_score(
                wpn_id=store.wpn_id,
                has_website=has_site,
                has_phone=store.phone is not None and len(store.phone) > 0,
                google_place_id=store.google_place_id,
                discovery_source=str(store.discovery_source),
                content_products=products,
                content_confidence=confidence,
            )

            rows.append({
                "store_id": str(store.id),
                "name": store.name,
                "city": city,
                "state": state,
                "status": str(store.status),
                "trust_score": result.score,
                "signals": "; ".join(result.signals),
            })

        # Sort by trust_score ascending (lowest trust first)
        rows.sort(key=lambda r: (r["trust_score"], r["name"]))

        # Write CSV
        fieldnames = [
            "store_id", "name", "city", "state", "status",
            "trust_score", "signals",
        ]
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        click.echo(f"Wrote {len(rows)} rows to {output}")

        # Summary stats
        if len(rows) > 0:
            scores = [int(r["trust_score"]) for r in rows]
            avg_score = sum(scores) / len(scores)
            low_trust = sum(1 for s in scores if s < 25)
            click.echo(f"Average trust score: {avg_score:.1f}")
            click.echo(f"Low trust (< 25): {low_trust}")
            click.echo(f"Score range: {min(scores)} - {max(scores)}")


if __name__ == "__main__":
    main()
