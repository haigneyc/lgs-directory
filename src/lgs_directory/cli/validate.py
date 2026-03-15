"""CLI commands for store validation."""

from __future__ import annotations

import logging
from uuid import UUID

import click
from rich.console import Console
from sqlalchemy import select

from lgs_directory.db import get_session
from lgs_directory.models.enums import PresenceStatus
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store

console = Console()


@click.group()
def validate() -> None:
    """Validate store data — web presence, platforms, singles."""


@validate.command()
@click.option("--store-id", type=str, default=None, help="Validate a specific store by UUID.")
@click.option(
    "--status", "status_filter", type=str, default="candidate",
    help="Filter stores by status.",
)
@click.option("--limit", type=int, default=100, help="Max stores to validate.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
def presence(
    store_id: str | None,
    status_filter: str,
    limit: int,
    verbose: bool,
) -> None:
    """Check web presence for store URLs."""
    from lgs_directory.validation.web_presence import detect_web_presence

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    with get_session() as session:
        if store_id:
            store = session.get(Store, UUID(store_id))
            if store is None:
                console.print(f"[red]Store not found:[/red] {store_id}")
                raise SystemExit(1)
            stores = [store]
        else:
            stmt = (
                select(Store)
                .where(Store.status == status_filter)
                .limit(limit)
            )
            stores = list(session.execute(stmt).scalars().all())

        assert isinstance(stores, list)
        console.print(f"Checking web presence for {len(stores)} stores...")

        total_checked = 0
        total_active = 0
        total_dead = 0

        for store in stores:
            updated = detect_web_presence(store, session)
            total_checked += len(updated)
            total_active += sum(1 for p in updated if p.status == PresenceStatus.ACTIVE)
            total_dead += sum(1 for p in updated if p.status == PresenceStatus.DEAD)

    console.print("\n[bold]Presence Check Results:[/bold]")
    console.print(f"  Stores processed:  {len(stores)}")
    console.print(f"  URLs checked:      {total_checked}")
    console.print(f"  Active:            {total_active}")
    console.print(f"  Dead/unreachable:  {total_dead}")


@validate.command()
@click.option("--store-id", type=str, default=None, help="Detect platform for a specific store.")
@click.option("--limit", type=int, default=100, help="Max presences to check.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
def platform(
    store_id: str | None,
    limit: int,
    verbose: bool,
) -> None:
    """Detect e-commerce platform for store websites."""
    from lgs_directory.validation.platform_detect import detect_and_log_platform

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    with get_session() as session:
        if store_id:
            stmt = (
                select(OnlinePresence)
                .where(OnlinePresence.store_id == UUID(store_id))
                .where(OnlinePresence.status == PresenceStatus.ACTIVE)
            )
        else:
            stmt = (
                select(OnlinePresence)
                .where(OnlinePresence.platform.is_(None))
                .where(OnlinePresence.status == PresenceStatus.ACTIVE)
                .limit(limit)
            )
        presences = list(session.execute(stmt).scalars().all())
        assert isinstance(presences, list)

        console.print(f"Detecting platforms for {len(presences)} presences...")

        results: dict[str, int] = {}
        for p in presences:
            detected = detect_and_log_platform(p, session)
            platform_name = detected.value
            results[platform_name] = results.get(platform_name, 0) + 1

    console.print("\n[bold]Platform Detection Results:[/bold]")
    for plat, count in sorted(results.items(), key=lambda x: -x[1]):
        console.print(f"  {plat}: {count}")


@validate.command()
@click.option("--store-id", type=str, default=None, help="Detect singles for a specific store.")
@click.option("--limit", type=int, default=100, help="Max presences to check.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
def singles(
    store_id: str | None,
    limit: int,
    verbose: bool,
) -> None:
    """Detect MTG singles availability on store websites."""
    from lgs_directory.config import get_settings
    from lgs_directory.validation.singles_detect import detect_singles

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    settings = get_settings()

    with get_session() as session:
        if store_id:
            stmt = (
                select(OnlinePresence)
                .where(OnlinePresence.store_id == UUID(store_id))
                .where(OnlinePresence.status == PresenceStatus.ACTIVE)
            )
        else:
            stmt = (
                select(OnlinePresence)
                .where(OnlinePresence.sells_mtg_singles.is_(None))
                .where(OnlinePresence.status == PresenceStatus.ACTIVE)
                .limit(limit)
            )
        presences = list(session.execute(stmt).scalars().all())
        assert isinstance(presences, list)

        console.print(f"Detecting MTG singles for {len(presences)} presences...")

        budget_remaining = settings.llm_budget_cents
        detected_count = 0

        for p in presences:
            result = detect_singles(
                url=p.url,
                platform=p.platform,
                anthropic_api_key=settings.anthropic_api_key,
                budget_remaining_cents=budget_remaining,
            )

            p.sells_mtg_singles = result.sells_mtg_singles
            if result.estimated_inventory_size is not None:
                p.estimated_inventory_size = result.estimated_inventory_size

            if result.sells_mtg_singles:
                detected_count += 1

            # Track LLM budget
            if result.method == "llm":
                budget_remaining = max(0, budget_remaining - 5)  # ~5 cents per call

    console.print("\n[bold]Singles Detection Results:[/bold]")
    console.print(f"  Presences checked:  {len(presences)}")
    console.print(f"  Sells singles:      {detected_count}")
    console.print(f"  No singles:         {len(presences) - detected_count}")


@validate.command()
@click.option(
    "--status", "status_filter", type=str, default="candidate",
    help="Filter stores by status.",
)
@click.option("--limit", type=int, default=100, help="Max stores to validate.")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would be done.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
def run(
    status_filter: str,
    limit: int,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Run the full validation pipeline (presence → platform → singles)."""
    from lgs_directory.config import get_settings
    from lgs_directory.validation.orchestrator import validate_stores

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    settings = get_settings()

    with get_session() as session:
        report = validate_stores(
            session,
            status_filter=status_filter,
            limit=limit,
            dry_run=dry_run,
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
