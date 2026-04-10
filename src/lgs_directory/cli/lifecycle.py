"""CLI commands for store lifecycle management."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

import click
from rich.console import Console
from rich.table import Table
from sqlalchemy import func, select

from lgs_directory.db import get_session
from lgs_directory.models.enums import StoreStatus
from lgs_directory.models.store import Store

console = Console()


def _load_known_google_place_ids() -> set[str]:
    """Return all Google place IDs already stored in the database."""
    with get_session() as session:
        stmt = select(Store.google_place_id).where(Store.google_place_id.isnot(None))
        rows = session.execute(stmt).scalars().all()
    known_ids = {place_id for place_id in rows if place_id}
    assert isinstance(known_ids, set)
    return known_ids


@click.group()
def lifecycle() -> None:
    """Manage store lifecycle — health checks, closures, re-crawls."""


@lifecycle.command()
@click.option("--limit", type=int, default=500, help="Max presences to check.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would be done.")
def health(limit: int, verbose: bool, dry_run: bool) -> None:
    """Run HTTP health checks on active/unresponsive store websites."""
    from lgs_directory.lifecycle.health import run_health_checks

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if dry_run:
        console.print("[yellow]Dry run — counting presences only.[/yellow]")
        with get_session() as session:
            from lgs_directory.models.enums import ChannelType
            from lgs_directory.models.online_presence import OnlinePresence

            count = session.execute(
                select(func.count(OnlinePresence.id))
                .join(Store)
                .where(Store.status.in_([StoreStatus.ACTIVE, StoreStatus.UNRESPONSIVE]))
                .where(OnlinePresence.channel_type == ChannelType.WEBSITE)
            ).scalar_one()
        console.print(f"Would check {count} presences (limit={limit})")
        return

    with get_session() as session:
        report = run_health_checks(session, limit=limit)

    console.print(f"\n[green]{report}[/green]")
    if report.errors > 0:
        console.print(f"\n[yellow]Errors ({report.errors}):[/yellow]")
        for detail in report.error_details[:20]:
            console.print(f"  - {detail}")
        if report.errors > 20:
            console.print(f"  ... and {report.errors - 20} more")


@lifecycle.command()
@click.option("--limit", type=int, default=200, help="Max stores to revalidate.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would be done.")
def revalidate(limit: int, verbose: bool, dry_run: bool) -> None:
    """Re-run platform and singles detection on active/verified stores."""
    from lgs_directory.lifecycle.health import run_full_revalidation

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if dry_run:
        console.print("[yellow]Dry run — counting stores only.[/yellow]")
        with get_session() as session:
            count = session.execute(
                select(func.count(Store.id))
                .where(Store.status.in_([StoreStatus.ACTIVE, StoreStatus.VERIFIED]))
            ).scalar_one()
        console.print(f"Would revalidate {count} stores (limit={limit})")
        return

    from lgs_directory.config import get_settings

    settings = get_settings()

    with get_session() as session:
        report = run_full_revalidation(
            session,
            limit=limit,
            anthropic_api_key=settings.anthropic_api_key,
            llm_budget_cents=settings.llm_budget_cents,
        )

    console.print(f"\n[green]{report}[/green]")
    if report.errors > 0:
        console.print(f"\n[yellow]Errors ({report.errors}):[/yellow]")
        for detail in report.error_details[:20]:
            console.print(f"  - {detail}")
        if report.errors > 20:
            console.print(f"  ... and {report.errors - 20} more")


@lifecycle.command(name="closure-check")
@click.option("--limit", type=int, default=500, help="Max stores to check.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
def closure_check(limit: int, verbose: bool) -> None:
    """Detect and mark closed stores among unresponsive ones."""
    from lgs_directory.config import get_settings
    from lgs_directory.lifecycle.closure import detect_closures

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    settings = get_settings()

    with get_session() as session:
        report = detect_closures(
            session,
            limit=limit,
            google_api_key=settings.google_places_api_key,
        )

    console.print(f"\n[green]{report}[/green]")
    if report.errors > 0:
        console.print(f"\n[yellow]Errors ({report.errors}):[/yellow]")
        for detail in report.error_details[:20]:
            console.print(f"  - {detail}")
        if report.errors > 20:
            console.print(f"  ... and {report.errors - 20} more")


_DEFAULT_WPN_CACHE = Path("data/wpn_raw.json")
_DEFAULT_GOOGLE_CACHE = Path("data/google_places_raw.json")


@lifecycle.command()
@click.option(
    "--source", type=click.Choice(["wpn", "google"]), required=True,
    help="Discovery source to re-crawl.",
)
@click.option(
    "--cache-file", type=click.Path(path_type=Path), default=None,
    help="Path to load raw data from cache.",
)
@click.option("--dry-run", is_flag=True, default=False, help="Show diff without writing.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
@click.option(
    "--max-requests", type=int, default=None, help="Google only: max API requests.",
)
@click.option(
    "--shard-index",
    type=int,
    default=None,
    help="Google only: zero-based grid shard to scan (requires --shard-count).",
)
@click.option(
    "--shard-count",
    type=int,
    default=None,
    help="Google only: total grid shards (requires --shard-index).",
)
@click.option(
    "--detail-tier",
    type=click.Choice(["none", "pro", "enterprise"]),
    default="enterprise",
    show_default=True,
    help="Google only: Place Details tier to fetch after ID-only search.",
)
@click.option(
    "--details-limit",
    type=int,
    default=None,
    help="Google only: max Place Details requests after search.",
)
@click.option(
    "--skip-details-for-known-google-ids/--include-known-google-ids",
    default=True,
    help="Google only: skip detail lookups for IDs already in the database.",
)
def recrawl(
    source: str,
    cache_file: Path | None,
    dry_run: bool,
    verbose: bool,
    max_requests: int | None,
    shard_index: int | None,
    shard_count: int | None,
    detail_tier: str,
    details_limit: int | None,
    skip_details_for_known_google_ids: bool,
) -> None:
    """Re-crawl a discovery source and diff against existing stores."""
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if (shard_index is None) != (shard_count is None):
        console.print("[red]--shard-index and --shard-count must be provided together[/red]")
        raise SystemExit(1)
    if shard_count is not None and shard_count <= 0:
        console.print("[red]--shard-count must be positive[/red]")
        raise SystemExit(1)
    if (
        shard_index is not None
        and shard_count is not None
        and (shard_index < 0 or shard_index >= shard_count)
    ):
        console.print("[red]--shard-index must be between 0 and shard-count - 1[/red]")
        raise SystemExit(1)

    if source == "wpn":
        from lgs_directory.discovery.wpn import (
            WpnScraper,
            load_raw_from_cache,
            save_raw_to_cache,
        )
        from lgs_directory.lifecycle.recrawl import recrawl_wpn_with_diff

        resolved_cache = cache_file or _DEFAULT_WPN_CACHE
        assert isinstance(resolved_cache, Path)

        if resolved_cache.exists():
            console.print(f"Loading WPN data from cache: {resolved_cache}")
            raw_stores = load_raw_from_cache(resolved_cache)
        else:
            # Fetch fresh
            cookies: dict[str, str] | None = None
            try:
                from lgs_directory.discovery.browser import get_akamai_cookies

                console.print("Harvesting Akamai cookies...")
                cookies = get_akamai_cookies()
            except (ImportError, Exception) as exc:
                console.print(f"[yellow]Cookie harvest skipped: {exc}[/yellow]")

            console.print("Fetching from WPN Store Locator...")
            scraper = WpnScraper(cookies=cookies)
            try:
                raw_stores = scraper.fetch_stores()
            finally:
                scraper.close()

            save_raw_to_cache(raw_stores, resolved_cache)

        # Filter to US
        us_states = {
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
            "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
            "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
            "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
            "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        }
        us_stores = [s for s in raw_stores if s.state.upper().strip() in us_states]

        with get_session() as session:
            report = recrawl_wpn_with_diff(session, us_stores, dry_run=dry_run)

    elif source == "google":
        from lgs_directory.discovery.google_places import (
            GooglePlacesScraper,
            load_raw_from_cache,
            save_raw_to_cache,
        )
        from lgs_directory.lifecycle.recrawl import recrawl_google_with_diff

        resolved_cache = cache_file or _DEFAULT_GOOGLE_CACHE
        assert isinstance(resolved_cache, Path)
        allow_google_delistings = shard_index is None and max_requests is None

        if resolved_cache.exists():
            console.print(f"Loading Google data from cache: {resolved_cache}")
            raw_stores = load_raw_from_cache(resolved_cache)
        else:
            from lgs_directory.config import get_settings

            settings = get_settings()
            if not settings.google_places_api_key:
                console.print("[red]GOOGLE_PLACES_API_KEY not set[/red]")
                raise SystemExit(1)

            known_place_ids: set[str] | None = None
            if skip_details_for_known_google_ids:
                known_place_ids = _load_known_google_place_ids()
                console.print(f"Loaded {len(known_place_ids)} known Google place IDs")

            console.print("Fetching from Google Places API...")
            scraper = GooglePlacesScraper(api_key=settings.google_places_api_key)
            try:
                raw_stores = scraper.fetch_stores(
                    max_requests=max_requests,
                    shard_index=shard_index,
                    shard_count=shard_count,
                    detail_tier=detail_tier,
                    details_limit=details_limit,
                    known_place_ids=known_place_ids,
                    skip_details_for_known_ids=skip_details_for_known_google_ids,
                )
            finally:
                scraper.close()

            save_raw_to_cache(raw_stores, resolved_cache)

        if not allow_google_delistings:
            console.print(
                "[yellow]Skipping Google delisting detection for partial/capped recrawl.[/yellow]"
            )

        with get_session() as session:
            report = recrawl_google_with_diff(
                session,
                raw_stores,
                dry_run=dry_run,
                allow_delistings=allow_google_delistings,
            )

    else:
        console.print(f"[red]Unknown source: {source}[/red]")
        raise SystemExit(1)

    console.print(f"\n[green]{report}[/green]")
    if report.delisted > 0:
        console.print(f"\n[yellow]Delisted stores: {report.delisted}[/yellow]")
    if report.errors > 0:
        console.print(f"\n[yellow]Errors ({report.errors}):[/yellow]")
        for detail in report.error_details[:20]:
            console.print(f"  - {detail}")
        if report.errors > 20:
            console.print(f"  ... and {report.errors - 20} more")


@lifecycle.command()
@click.option("--store-id", type=str, required=True, help="Store UUID.")
@click.option(
    "--to-status", type=click.Choice([s.value for s in StoreStatus]), required=True,
    help="Target status.",
)
@click.option("--reason", type=str, required=True, help="Reason for transition.")
def transition(store_id: str, to_status: str, reason: str) -> None:
    """Manually transition a store's status."""
    from lgs_directory.lifecycle.transitions import transition_store

    target = StoreStatus(to_status)

    with get_session() as session:
        store = session.get(Store, UUID(store_id))
        if store is None:
            console.print(f"[red]Store not found:[/red] {store_id}")
            raise SystemExit(1)

        console.print(f"Store: {store.name} (current: {store.status})")

        success = transition_store(store, target, session, reason=reason)
        if success:
            console.print(f"[green]Transitioned to {target.value}[/green]")
        else:
            console.print(
                f"[red]Invalid transition: {store.status} → {target.value}[/red]"
            )
            raise SystemExit(1)


@lifecycle.command()
def status() -> None:
    """Show store counts by lifecycle status."""
    with get_session() as session:
        total = session.execute(
            select(func.count(Store.id))
        ).scalar_one()

        status_counts = session.execute(
            select(Store.status, func.count(Store.id))
            .group_by(Store.status)
        ).all()

    console.print(f"\n[bold]Lifecycle Status[/bold] ({total} total stores)")

    if status_counts:
        table = Table()
        table.add_column("Status")
        table.add_column("Count", justify="right")
        table.add_column("Pct", justify="right")

        for st, count in sorted(status_counts, key=lambda x: -x[1]):
            pct = f"{count / total * 100:.1f}%" if total > 0 else "—"
            table.add_row(str(st), str(count), pct)

        console.print(table)
    else:
        console.print("  No stores found.")

    console.print()
