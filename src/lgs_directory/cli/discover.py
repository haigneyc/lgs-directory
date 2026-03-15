"""CLI commands for store discovery."""

from __future__ import annotations

import logging
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from sqlalchemy import func, select

from lgs_directory.db import get_session
from lgs_directory.models.store import Store

console = Console()

_DEFAULT_CACHE_PATH = Path("data/wpn_raw.json")


@click.group()
def discover() -> None:
    """Discover stores from external sources."""


@discover.command()
@click.option(
    "--cache-file",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to save/load raw WPN data (JSON). Defaults to data/wpn_raw.json.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Fetch and show stats without writing to the database.",
)
@click.option(
    "--from-cache",
    is_flag=True,
    default=False,
    help="Load from cache file instead of fetching from API.",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose logging.",
)
def wpn(
    cache_file: Path | None,
    dry_run: bool,
    from_cache: bool,
    verbose: bool,
) -> None:
    """Fetch and ingest stores from the WPN Store Locator."""
    from lgs_directory.discovery.ingest import ingest_wpn_stores
    from lgs_directory.discovery.wpn import (
        WpnScraper,
        WpnStoreRaw,
        load_raw_from_cache,
        save_raw_to_cache,
    )

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    resolved_cache = cache_file or _DEFAULT_CACHE_PATH
    assert isinstance(resolved_cache, Path)

    stores: list[WpnStoreRaw]

    if from_cache:
        if not resolved_cache.exists():
            console.print(f"[red]Cache file not found:[/red] {resolved_cache}")
            raise SystemExit(1)
        console.print(f"Loading from cache: {resolved_cache}")
        stores = load_raw_from_cache(resolved_cache)
    else:
        # Try to harvest Akamai cookies for bot bypass
        cookies: dict[str, str] | None = None
        try:
            from lgs_directory.discovery.browser import get_akamai_cookies

            console.print("Harvesting Akamai cookies via browser...")
            cookies = get_akamai_cookies()
            console.print(f"[green]Got {len(cookies)} Akamai cookies[/green]")
        except ImportError:
            console.print("[yellow]Playwright not installed — skipping cookie harvest[/yellow]")
        except Exception as exc:
            console.print(f"[yellow]Cookie harvest failed ({exc}) — continuing without[/yellow]")

        console.print("Fetching stores from WPN Store Locator...")
        scraper = WpnScraper(cookies=cookies)
        try:
            stores = scraper.fetch_stores()
        finally:
            scraper.close()

        # Save to cache
        console.print(f"Saving {len(stores)} stores to cache: {resolved_cache}")
        save_raw_to_cache(stores, resolved_cache)

    # Filter to US stores only
    us_states = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
        "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
        "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
        "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
        "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    }
    us_stores = [s for s in stores if s.state.upper().strip() in us_states]

    # Show stats
    premium_count = sum(1 for s in us_stores if s.is_premium)
    console.print("\n[bold]WPN Discovery Results:[/bold]")
    console.print(f"  Total fetched:    {len(stores)}")
    console.print(f"  US stores:        {len(us_stores)}")
    console.print(f"  WPN Premium:      {premium_count}")
    console.print(f"  WPN Core:         {len(us_stores) - premium_count}")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes written to database.[/yellow]")

        # Show state breakdown
        state_counts: dict[str, int] = {}
        for s in us_stores:
            st = s.state.upper().strip()
            state_counts[st] = state_counts.get(st, 0) + 1

        table = Table(title="Stores by State (top 15)")
        table.add_column("State")
        table.add_column("Count", justify="right")
        for st, count in sorted(state_counts.items(), key=lambda x: -x[1])[:15]:
            table.add_row(st, str(count))
        console.print(table)
        return

    # Ingest into database
    console.print("\nIngesting into database...")
    with get_session() as session:
        report = ingest_wpn_stores(us_stores, session)

    console.print(f"\n[green]{report}[/green]")
    if report.errors > 0:
        console.print(f"\n[yellow]Errors ({report.errors}):[/yellow]")
        for detail in report.error_details[:20]:
            console.print(f"  - {detail}")
        if report.errors > 20:
            console.print(f"  ... and {report.errors - 20} more")


_DEFAULT_GOOGLE_CACHE_PATH = Path("data/google_places_raw.json")


@discover.command()
@click.option(
    "--cache-file",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to save/load raw Google Places data (JSON).",
)
@click.option("--dry-run", is_flag=True, default=False, help="Show stats without writing.")
@click.option("--from-cache", is_flag=True, default=False, help="Load from cache file.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
@click.option("--limit-cells", type=int, default=None, help="Limit grid cells for testing.")
@click.option(
    "--max-requests", type=int, default=None, help="Max API requests (cost control).",
)
def google(
    cache_file: Path | None,
    dry_run: bool,
    from_cache: bool,
    verbose: bool,
    limit_cells: int | None,
    max_requests: int | None,
) -> None:
    """Fetch and ingest stores from Google Places API."""
    from lgs_directory.config import get_settings
    from lgs_directory.discovery.google_places import (
        GooglePlaceRaw,
        GooglePlacesScraper,
        load_raw_from_cache,
        save_raw_to_cache,
    )
    from lgs_directory.discovery.ingest_google import ingest_google_stores

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    resolved_cache = cache_file or _DEFAULT_GOOGLE_CACHE_PATH
    assert isinstance(resolved_cache, Path)

    stores: list[GooglePlaceRaw]

    if from_cache:
        if not resolved_cache.exists():
            console.print(f"[red]Cache file not found:[/red] {resolved_cache}")
            raise SystemExit(1)
        console.print(f"Loading from cache: {resolved_cache}")
        stores = load_raw_from_cache(resolved_cache)
    else:
        settings = get_settings()
        if not settings.google_places_api_key:
            console.print("[red]GOOGLE_PLACES_API_KEY not set in environment[/red]")
            raise SystemExit(1)

        console.print("Fetching stores from Google Places API...")
        scraper = GooglePlacesScraper(
            api_key=settings.google_places_api_key,
        )
        try:
            stores = scraper.fetch_stores(
                limit_cells=limit_cells,
                max_requests=max_requests,
            )
        finally:
            scraper.close()

        console.print(f"Saving {len(stores)} stores to cache: {resolved_cache}")
        save_raw_to_cache(stores, resolved_cache)

    console.print("\n[bold]Google Places Discovery Results:[/bold]")
    console.print(f"  Total found: {len(stores)}")

    with_website = sum(1 for s in stores if s.website)
    with_phone = sum(1 for s in stores if s.phone)
    console.print(f"  With website: {with_website}")
    console.print(f"  With phone:   {with_phone}")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes written to database.[/yellow]")
        return

    console.print("\nIngesting into database...")
    with get_session() as session:
        report = ingest_google_stores(stores, session)

    console.print(f"\n[green]{report}[/green]")
    if report.errors > 0:
        console.print(f"\n[yellow]Errors ({report.errors}):[/yellow]")
        for detail in report.error_details[:20]:
            console.print(f"  - {detail}")
        if report.errors > 20:
            console.print(f"  ... and {report.errors - 20} more")


@discover.command()
def status() -> None:
    """Show discovery statistics."""
    with get_session() as session:
        # Total stores
        total = session.execute(select(func.count(Store.id))).scalar_one()

        # By source
        source_counts = session.execute(
            select(Store.discovery_source, func.count(Store.id))
            .group_by(Store.discovery_source)
        ).all()

        # By status
        status_counts = session.execute(
            select(Store.status, func.count(Store.id))
            .group_by(Store.status)
        ).all()

        # Stores with WPN IDs
        wpn_count = session.execute(
            select(func.count(Store.id)).where(Store.wpn_id.isnot(None))
        ).scalar_one()

    console.print("\n[bold]Discovery Status[/bold]")
    console.print(f"  Total stores: {total}")
    console.print(f"  With WPN ID:  {wpn_count}")

    if source_counts:
        table = Table(title="By Source")
        table.add_column("Source")
        table.add_column("Count", justify="right")
        for source, count in sorted(source_counts, key=lambda x: -x[1]):
            table.add_row(str(source), str(count))
        console.print(table)

    if status_counts:
        table = Table(title="By Status")
        table.add_column("Status")
        table.add_column("Count", justify="right")
        for st, count in sorted(status_counts, key=lambda x: -x[1]):
            table.add_row(str(st), str(count))
        console.print(table)

    console.print()
