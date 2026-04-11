"""CLI commands for freshness and pricing detection."""

from __future__ import annotations

import logging
from uuid import UUID

import click
from rich.console import Console
from sqlalchemy import select
from sqlalchemy.orm import Session

from lgs_directory.db import get_session
from lgs_directory.models.enums import ChannelType, PresenceStatus, StoreStatus
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store
from lgs_directory.validation.pricing_detect import _ECOMMERCE_PLATFORMS

console = Console()


@click.group()
def freshness() -> None:
    """Freshness & pricing detection — detect price staleness and sync status."""


@freshness.command()
@click.option("--store-id", type=str, default=None, help="Check a specific store by UUID.")
@click.option("--limit", type=int, default=100, help="Max presences to check.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would be checked.")
def scan(
    store_id: str | None,
    limit: int,
    verbose: bool,
    dry_run: bool,
) -> None:
    """Run freshness detection only (HTTP headers, sitemap, page timestamps)."""
    from lgs_directory.validation.freshness_detect import detect_freshness

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    with get_session() as session:
        presences = _get_eligible_presences(session, store_id, limit)
        assert isinstance(presences, list)

        console.print(f"Scanning freshness for {len(presences)} presences...")

        if dry_run:
            for p in presences:
                console.print(f"  Would check: {p.url}")
            return

        results: dict[str, int] = {"found": 0, "none": 0}

        for p in presences:
            result = detect_freshness(p.url)
            if result.last_update_detected is not None:
                results["found"] += 1
                if verbose:
                    console.print(
                        f"  [green]{p.url}[/green] → {result.method} "
                        f"({result.last_update_detected.date()})"
                    )
            else:
                results["none"] += 1
                if verbose:
                    console.print(f"  [dim]{p.url}[/dim] → no signal")

    console.print("\n[bold]Freshness Scan Results:[/bold]")
    console.print(f"  Presences scanned:  {len(presences)}")
    console.print(f"  Signal found:       {results['found']}")
    console.print(f"  No signal:          {results['none']}")


@freshness.command()
@click.option("--store-id", type=str, default=None, help="Check a specific store by UUID.")
@click.option("--limit", type=int, default=100, help="Max presences to check.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would be checked.")
def pricing(
    store_id: str | None,
    limit: int,
    verbose: bool,
    dry_run: bool,
) -> None:
    """Run pricing detection only (card search + price comparison)."""
    from lgs_directory.validation.pricing_detect import detect_and_log_pricing
    from lgs_directory.validation.scryfall import fetch_probe_prices

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    console.print("Fetching market reference prices...")
    market_prices = fetch_probe_prices()
    if len(market_prices) == 0:
        console.print("[red]Failed to fetch market prices — aborting[/red]")
        raise SystemExit(1)

    console.print(f"  Got {len(market_prices)} probe card prices")

    with get_session() as session:
        presences = _get_eligible_presences(session, store_id, limit)
        assert isinstance(presences, list)

        console.print(f"Running pricing detection for {len(presences)} presences...")

        if dry_run:
            for p in presences:
                console.print(f"  Would check: {p.url}")
            return

        synced = 0
        manual = 0
        unknown = 0

        for p in presences:
            result = detect_and_log_pricing(p, session, market_prices)
            session.commit()
            if result.pricing_method.value == "synced":
                synced += 1
            elif result.pricing_method.value == "manual":
                manual += 1
            else:
                unknown += 1

            if verbose:
                console.print(
                    f"  {p.url} → [bold]{result.pricing_method.value}[/bold] "
                    f"({result.cards_found}/{result.cards_searched} cards, "
                    f"{result.avg_delta_pct:.1f}% avg delta)"
                )

    console.print("\n[bold]Pricing Detection Results:[/bold]")
    console.print(f"  Presences checked:  {len(presences)}")
    console.print(f"  Synced:             {synced}")
    console.print(f"  Manual:             {manual}")
    console.print(f"  Unknown:            {unknown}")


@freshness.command(name="run")
@click.option("--limit", type=int, default=100, help="Max presences to process.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would be done.")
def run_pipeline(
    limit: int,
    verbose: bool,
    dry_run: bool,
) -> None:
    """Run the full freshness + pricing pipeline."""
    from lgs_directory.validation.pricing_detect import run_pricing_detection

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if dry_run:
        with get_session() as session:
            presences = _get_eligible_presences(session, store_id=None, limit=limit)
            console.print(f"Would process {len(presences)} presences")
            for p in presences:
                console.print(f"  {p.url}")
        return

    report = run_pricing_detection(limit=limit)

    console.print(f"\n[green]{report}[/green]")

    if report.errors > 0:
        console.print(f"\n[yellow]Errors ({report.errors}):[/yellow]")
        for detail in report.error_details[:20]:
            console.print(f"  - {detail}")
        if report.errors > 20:
            console.print(f"  ... and {report.errors - 20} more")


def _get_eligible_presences(
    session: Session,
    store_id: str | None,
    limit: int,
) -> list[OnlinePresence]:
    """Query eligible presences for freshness/pricing checks.

    Eligible: website channel, active presence, active store, sells MTG singles.
    """
    assert limit > 0, "Limit must be positive"

    if store_id:
        stmt = (
            select(OnlinePresence)
            .where(OnlinePresence.store_id == UUID(store_id))
            .where(OnlinePresence.channel_type == ChannelType.WEBSITE)
            .where(OnlinePresence.status == PresenceStatus.ACTIVE)
        )
    else:
        platform_values = [p.value for p in _ECOMMERCE_PLATFORMS]
        assert len(platform_values) > 0, "Must have at least one e-commerce platform"
        stmt = (
            select(OnlinePresence)
            .join(Store)
            .where(Store.status == StoreStatus.ACTIVE)
            .where(OnlinePresence.channel_type == ChannelType.WEBSITE)
            .where(OnlinePresence.status == PresenceStatus.ACTIVE)
            .where(OnlinePresence.sells_mtg_singles.is_(True))
            .where(OnlinePresence.platform.in_(platform_values))
            .limit(limit)
        )

    presences = list(session.execute(stmt).scalars().all())
    assert isinstance(presences, list)
    return presences
