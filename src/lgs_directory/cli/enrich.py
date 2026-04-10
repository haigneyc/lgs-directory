"""CLI commands for enriching store data from external APIs."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime, timedelta

import click
import httpx
from rich.console import Console
from sqlalchemy import select

from lgs_directory.config import get_settings
from lgs_directory.db import get_session
from lgs_directory.models.enums import StoreStatus
from lgs_directory.models.store import Store
from lgs_directory.models.store_external_ref import StoreExternalRef

console = Console()
logger = logging.getLogger(__name__)

PROVIDER_GOOGLE_PLACES = "google_places"
_RATE_LIMIT_SECS = 0.1  # 10 req/sec
_MAX_STORES = 10_000
_MATCH_GOOGLE_MAX_LIMIT = 10_000
_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_STALE_DAYS = 30
_MAX_RETRIES = 3
_RETRY_BACKOFF_SECS = 5


@click.group()
def enrich() -> None:
    """Enrich stores with external data."""


@enrich.command()
@click.option("--limit", default=_MAX_STORES, help="Max stores to enrich")
@click.option("--dry-run", is_flag=True, help="Show what would be enriched")
@click.option("--force", is_flag=True, help="Re-enrich all stores regardless of age")
@click.option("--verbose", is_flag=True, help="Verbose logging")
def google(limit: int, dry_run: bool, force: bool, verbose: bool) -> None:
    """Enrich stores with Google Places data (hours, rating, photos)."""
    assert isinstance(limit, int), "limit must be an int"
    assert limit > 0, "limit must be positive"

    settings = get_settings()
    api_key = settings.google_places_api_key
    if not api_key:
        console.print("[red]GOOGLE_PLACES_API_KEY not set[/red]")
        raise SystemExit(1)

    bounded_limit = min(limit, _MAX_STORES)

    with get_session() as session:
        # Find stores needing enrichment
        stores = _find_stores_needing_enrichment(session, bounded_limit, force)

        if not stores:
            console.print("[green]No stores need enrichment.[/green]")
            return

        console.print(f"\n[bold]Google Places Enrichment[/bold]")
        console.print(f"  Stores needing enrichment: {len(stores)}")

        if dry_run:
            for i, (store_id, name, place_id) in enumerate(stores):
                console.print(f"  [{i+1}/{len(stores)}] Would enrich \"{name}\" ({place_id})")
            return

        enriched = 0
        skipped = 0
        errors = 0

        for i, (store_id, name, place_id) in enumerate(stores):
            assert place_id is not None, "place_id must not be None"
            assert len(place_id) > 0, "place_id must not be empty"

            payload = _fetch_place_details(api_key, place_id, verbose)
            if payload is None:
                skipped += 1
                continue

            try:
                _upsert_enrichment(session, store_id, place_id, payload)
                session.commit()
                enriched += 1

                rating = payload.get("rating", "n/a")
                hours_count = len(payload.get("hours", {}).get("weekday_text", []))
                photo_count = len(payload.get("photo_refs", []))
                console.print(
                    f"  [{i+1}/{len(stores)}] Enriched \"{name}\" "
                    f"-- rating: {rating}, hours: {hours_count} days, photos: {photo_count}"
                )
            except Exception as exc:
                session.rollback()
                errors += 1
                logger.error("Failed to upsert enrichment for %s: %s", name, exc)
                if verbose:
                    console.print(f"  [{i+1}/{len(stores)}] [red]Error: {exc}[/red]")

            time.sleep(_RATE_LIMIT_SECS)

        console.print(f"\n[bold]Results:[/bold]")
        console.print(f"  Enriched: {enriched}")
        console.print(f"  Skipped:  {skipped}")
        console.print(f"  Errors:   {errors}")


def _find_stores_needing_enrichment(
    session, limit: int, force: bool
) -> list[tuple]:
    """Find stores with google_place_id that need enrichment."""
    assert isinstance(limit, int), "limit must be int"
    assert limit > 0, "limit must be positive"

    # Get all stores with a google_place_id
    stmt = (
        select(Store.id, Store.name, Store.google_place_id)
        .where(Store.google_place_id.isnot(None))
        .where(Store.google_place_id != "")
        .order_by(Store.name)
        .limit(limit)
    )
    candidates = session.execute(stmt).all()

    if force:
        return list(candidates)

    # Filter out stores already enriched within STALE_DAYS
    cutoff = datetime.now(UTC) - timedelta(days=_STALE_DAYS)
    results = []
    max_check = min(len(candidates), _MAX_STORES)

    for i in range(max_check):
        store_id, name, place_id = candidates[i]
        existing = session.execute(
            select(StoreExternalRef.payload)
            .where(StoreExternalRef.store_id == store_id)
            .where(StoreExternalRef.provider == PROVIDER_GOOGLE_PLACES)
            .limit(1)
        ).scalar_one_or_none()

        if existing is None:
            results.append((store_id, name, place_id))
        elif isinstance(existing, dict):
            enriched_at = existing.get("enriched_at")
            if enriched_at:
                try:
                    ts = datetime.fromisoformat(enriched_at.replace("Z", "+00:00"))
                    if ts < cutoff:
                        results.append((store_id, name, place_id))
                except (ValueError, TypeError):
                    results.append((store_id, name, place_id))
            else:
                results.append((store_id, name, place_id))

    result = results[:limit]
    assert isinstance(result, list), "results must be a list"
    assert all(isinstance(r, tuple) and len(r) == 3 for r in result), "each result must be a 3-tuple"
    return result


def _fetch_place_details(
    api_key: str, place_id: str, verbose: bool = False
) -> dict | None:
    """Fetch place details from Google Places API v2."""
    assert isinstance(api_key, str), "api_key must be a string"
    assert isinstance(place_id, str), "place_id must be a string"

    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "regularOpeningHours,rating,userRatingCount,photos",
    }

    for attempt in range(_MAX_RETRIES):
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(url, headers=headers)

            if resp.status_code == 404:
                if verbose:
                    logger.warning("Place not found: %s", place_id)
                return None

            if resp.status_code == 429:
                wait = _RETRY_BACKOFF_SECS * (attempt + 1)
                logger.warning("Rate limited, backing off %ds", wait)
                time.sleep(wait)
                continue

            resp.raise_for_status()
            data = resp.json()
            return _parse_enrichment_payload(data)

        except httpx.HTTPError as exc:
            logger.error("HTTP error for %s (attempt %d): %s", place_id, attempt + 1, exc)
            if attempt == _MAX_RETRIES - 1:
                return None
            time.sleep(_RETRY_BACKOFF_SECS)

    return None


def _parse_enrichment_payload(data: dict) -> dict:
    """Parse Google Places API response into enrichment payload."""
    assert isinstance(data, dict), "data must be a dict"

    payload: dict = {
        "enriched_at": datetime.now(UTC).isoformat(),
    }

    # Hours
    hours = data.get("regularOpeningHours")
    if hours:
        payload["hours"] = {
            "weekday_text": hours.get("weekdayDescriptions", []),
            "periods": hours.get("periods", []),
        }

    # Rating
    if "rating" in data:
        payload["rating"] = data["rating"]
    if "userRatingCount" in data:
        payload["user_rating_count"] = data["userRatingCount"]

    # Photos (just references, not downloads)
    photos = data.get("photos", [])
    photo_refs = []
    max_photos = min(len(photos), 10)
    for i in range(max_photos):
        name = photos[i].get("name", "")
        if name:
            photo_refs.append(name)
    payload["photo_refs"] = photo_refs

    assert "enriched_at" in payload, "payload must have enriched_at"
    return payload


def _upsert_enrichment(
    session, store_id, place_id: str, payload: dict
) -> None:
    """Upsert enrichment data into store_external_refs."""
    assert isinstance(place_id, str), "place_id must be a string"
    assert isinstance(payload, dict), "payload must be a dict"

    existing = session.execute(
        select(StoreExternalRef)
        .where(StoreExternalRef.provider == PROVIDER_GOOGLE_PLACES)
        .where(StoreExternalRef.external_id == place_id)
    ).scalar_one_or_none()

    now = datetime.now(UTC)

    if existing:
        existing.payload = payload
        existing.last_seen = now
    else:
        ref = StoreExternalRef(
            store_id=store_id,
            provider=PROVIDER_GOOGLE_PLACES,
            external_id=place_id,
            payload=payload,
            first_seen=now,
            last_seen=now,
        )
        session.add(ref)


# ---------------------------------------------------------------------------
# match-google: find Google Place IDs for stores that lack one
# ---------------------------------------------------------------------------


@enrich.command("match-google")
@click.option("--limit", default=100, help="Max stores to process")
@click.option("--dry-run", is_flag=True, help="Show matches without saving")
@click.option("--verbose", is_flag=True, help="Verbose logging")
def match_google(limit: int, dry_run: bool, verbose: bool) -> None:
    """Find Google Place IDs for stores that don't have one."""
    assert isinstance(limit, int), "limit must be an int"
    assert limit > 0, "limit must be positive"

    settings = get_settings()
    api_key = settings.google_places_api_key
    if not api_key:
        console.print("[red]GOOGLE_PLACES_API_KEY not set[/red]")
        raise SystemExit(1)

    bounded_limit = min(limit, _MATCH_GOOGLE_MAX_LIMIT)

    with get_session() as session:
        stores = _find_stores_without_place_id(session, bounded_limit)

        if not stores:
            console.print("[green]All stores already have a Google Place ID.[/green]")
            return

        total = len(stores)
        console.print(f"\n[bold]Google Place ID Matching[/bold]")
        console.print(f"  Stores without Place ID: {total}")
        if dry_run:
            console.print("  Mode: dry-run (no changes will be saved)\n")

        matched = 0
        skipped = 0
        errors = 0

        for i in range(total):
            store_id, name, city, state = stores[i]

            place_id = _search_google_place(api_key, name, city, state, verbose)

            if place_id is None:
                skipped += 1
                if verbose:
                    console.print(
                        f"  [{i + 1}/{total}] No match for \"{name}\" "
                        f"({city}, {state})"
                    )
                time.sleep(_RATE_LIMIT_SECS)
                continue

            if dry_run:
                console.print(
                    f"  [{i + 1}/{total}] Would match \"{name}\" -> {place_id}"
                )
            else:
                try:
                    _update_store_place_id(session, store_id, place_id)
                    session.commit()
                    matched += 1
                    console.print(
                        f"  [{i + 1}/{total}] Matched \"{name}\" -> {place_id}"
                    )
                except Exception as exc:
                    session.rollback()
                    errors += 1
                    logger.error(
                        "Failed to update place_id for %s: %s", name, exc
                    )
                    if verbose:
                        console.print(
                            f"  [{i + 1}/{total}] [red]Error: {exc}[/red]"
                        )

            time.sleep(_RATE_LIMIT_SECS)

        console.print(f"\n[bold]Results:[/bold]")
        console.print(f"  Matched: {matched}")
        console.print(f"  Skipped: {skipped}")
        console.print(f"  Errors:  {errors}")


def _find_stores_without_place_id(
    session, limit: int
) -> list[tuple]:
    """Find stores that have no google_place_id and are not closed."""
    assert isinstance(limit, int), "limit must be int"
    assert limit > 0, "limit must be positive"

    stmt = (
        select(
            Store.id,
            Store.name,
            Store.address["city"].astext.label("city"),
            Store.address["state"].astext.label("state"),
        )
        .where(
            (Store.google_place_id.is_(None)) | (Store.google_place_id == "")
        )
        .where(Store.status != StoreStatus.CLOSED)
        .order_by(Store.name)
        .limit(limit)
    )
    rows = session.execute(stmt).all()
    assert isinstance(rows, list), "query must return a list"
    return rows


def _search_google_place(
    api_key: str,
    store_name: str,
    city: str,
    state: str,
    verbose: bool = False,
) -> str | None:
    """Search Google Places Text Search for a store and return its Place ID.

    Returns None if no result is found.
    """
    assert isinstance(api_key, str) and len(api_key) > 0, "api_key required"
    assert isinstance(store_name, str) and len(store_name) > 0, "store_name required"

    query = f"{store_name}, {city}, {state}"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress",
    }
    body = {
        "textQuery": query,
        "maxResultCount": 1,
    }

    for attempt in range(_MAX_RETRIES):
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.post(_TEXT_SEARCH_URL, json=body, headers=headers)

            if resp.status_code == 429:
                wait = _RETRY_BACKOFF_SECS * (attempt + 1)
                logger.warning("Rate limited, backing off %ds", wait)
                time.sleep(wait)
                continue

            resp.raise_for_status()
            data = resp.json()
            assert isinstance(data, dict), "API response must be a dict"

            places = data.get("places", [])
            if len(places) == 0:
                return None

            place_id = places[0].get("id", "")
            if not place_id:
                return None

            if verbose:
                display_name = places[0].get("displayName", {}).get("text", "")
                address = places[0].get("formattedAddress", "")
                logger.info(
                    "Matched %s -> %s (%s, %s)",
                    query, place_id, display_name, address,
                )

            return place_id

        except httpx.HTTPError as exc:
            logger.error(
                "HTTP error searching for '%s' (attempt %d): %s",
                query, attempt + 1, exc,
            )
            if attempt == _MAX_RETRIES - 1:
                return None
            time.sleep(_RETRY_BACKOFF_SECS)

    return None


def _update_store_place_id(session, store_id, place_id: str) -> None:
    """Set the google_place_id on a store record."""
    assert isinstance(place_id, str), "place_id must be a string"
    assert len(place_id) > 0, "place_id must not be empty"

    store = session.get(Store, store_id)
    assert store is not None, f"Store {store_id} not found"
    store.google_place_id = place_id
