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

# Upper bound for CLI store lists (safety cap for loop bounds)
_MAX_CLI_STORES = 100_000

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
        "AL",
        "AK",
        "AZ",
        "AR",
        "CA",
        "CO",
        "CT",
        "DE",
        "DC",
        "FL",
        "GA",
        "HI",
        "ID",
        "IL",
        "IN",
        "IA",
        "KS",
        "KY",
        "LA",
        "ME",
        "MD",
        "MA",
        "MI",
        "MN",
        "MS",
        "MO",
        "MT",
        "NE",
        "NV",
        "NH",
        "NJ",
        "NM",
        "NY",
        "NC",
        "ND",
        "OH",
        "OK",
        "OR",
        "PA",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
    }
    us_stores = [s for s in stores if s.state.upper().strip() in us_states]

    assert isinstance(us_stores, list), "us_stores must be a list"
    assert len(us_stores) <= _MAX_CLI_STORES, f"Store count {len(us_stores)} exceeds cap"

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


def _load_known_google_place_ids() -> set[str]:
    """Return all Google place IDs already stored in the database."""
    with get_session() as session:
        stmt = select(Store.google_place_id).where(Store.google_place_id.isnot(None))
        rows = session.execute(stmt).scalars().all()
    known_ids = {place_id for place_id in rows if place_id}
    assert isinstance(known_ids, set), "known_ids must be a set"
    return known_ids


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
    "--max-requests",
    type=int,
    default=None,
    help="Max API requests (cost control).",
)
@click.option(
    "--shard-index",
    type=int,
    default=None,
    help="Zero-based grid shard to scan (requires --shard-count).",
)
@click.option(
    "--shard-count",
    type=int,
    default=None,
    help="Total number of grid shards (requires --shard-index).",
)
@click.option(
    "--detail-tier",
    type=click.Choice(["none", "pro", "enterprise"]),
    default="enterprise",
    show_default=True,
    help="Place Details tier (accepted for compatibility; search-only in current build).",
)
@click.option(
    "--details-limit",
    type=int,
    default=None,
    help="Max number of Place Details requests (accepted for compatibility).",
)
@click.option(
    "--skip-known-ids/--include-known-ids",
    default=True,
    help="Skip fetching details for place IDs already in the database.",
)
def google(
    cache_file: Path | None,
    dry_run: bool,
    from_cache: bool,
    verbose: bool,
    limit_cells: int | None,
    max_requests: int | None,
    shard_index: int | None,
    shard_count: int | None,
    detail_tier: str,
    details_limit: int | None,
    skip_known_ids: bool,
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

    assert detail_tier in {"none", "pro", "enterprise"}, f"invalid detail_tier: {detail_tier}"

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

        if shard_index is not None and shard_count is not None:
            console.print(f"Grid shard: {shard_index + 1}/{shard_count}")

        console.print("Fetching stores from Google Places API...")
        scraper = GooglePlacesScraper(
            api_key=settings.google_places_api_key,
        )
        try:
            stores = scraper.fetch_stores(
                limit_cells=limit_cells,
                max_requests=max_requests,
                shard_index=shard_index,
                shard_count=shard_count,
            )
        finally:
            scraper.close()

        console.print(f"Saving {len(stores)} stores to cache: {resolved_cache}")
        save_raw_to_cache(stores, resolved_cache)

    assert isinstance(stores, list), "stores must be a list"
    assert len(stores) <= _MAX_CLI_STORES, f"Store count {len(stores)} exceeds cap"

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
    from sqlalchemy import text as sa_text

    with get_session() as session:
        # Total stores
        total = session.execute(select(func.count(Store.id))).scalar_one()
        assert isinstance(total, int), "total must be an int"

        # By source
        source_counts = session.execute(
            select(Store.discovery_source, func.count(Store.id)).group_by(Store.discovery_source)
        ).all()

        # By status
        status_counts = session.execute(
            select(Store.status, func.count(Store.id)).group_by(Store.status)
        ).all()

        # Stores with WPN IDs
        wpn_count = session.execute(
            select(func.count(Store.id)).where(Store.wpn_id.isnot(None))
        ).scalar_one()

        # Category breakdown from store_categories junction table
        category_counts = session.execute(
            sa_text(
                "SELECT category, count(*)::int as cnt"
                " FROM store_categories"
                " GROUP BY category"
                " ORDER BY cnt DESC"
            )
        ).all()

    assert isinstance(wpn_count, int), "wpn_count must be an int"

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

    if category_counts:
        table = Table(title="By Category")
        table.add_column("Category")
        table.add_column("Count", justify="right")
        for cat, count in category_counts:
            table.add_row(str(cat), str(count))
        console.print(table)

    console.print()


_DEFAULT_GW_CACHE_PATH = Path("data/gw_raw.json")


@discover.command(name="games-workshop")
@click.option(
    "--cache-file",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to save/load raw GW data (JSON). Defaults to data/gw_raw.json.",
)
@click.option("--dry-run", is_flag=True, default=False, help="Show stats without writing.")
@click.option("--from-cache", is_flag=True, default=False, help="Load from cache file.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
@click.option(
    "--max-requests",
    type=int,
    default=None,
    help="Max API requests (limits grid scan).",
)
def games_workshop(
    cache_file: Path | None,
    dry_run: bool,
    from_cache: bool,
    verbose: bool,
    max_requests: int | None,
) -> None:
    """Fetch and ingest stores from the Games Workshop Retailer Locator."""
    from lgs_directory.discovery.games_workshop import (
        GamesWorkshopScraper,
        GamesWorkshopStoreRaw,
        load_raw_from_cache,
        save_raw_to_cache,
    )
    from lgs_directory.discovery.ingest_games_workshop import ingest_gw_stores

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    resolved_cache = cache_file or _DEFAULT_GW_CACHE_PATH
    assert isinstance(resolved_cache, Path)

    stores: list[GamesWorkshopStoreRaw]

    if from_cache:
        if not resolved_cache.exists():
            console.print(f"[red]Cache file not found:[/red] {resolved_cache}")
            raise SystemExit(1)
        console.print(f"Loading from cache: {resolved_cache}")
        stores = load_raw_from_cache(resolved_cache)
    else:
        console.print("Fetching stores from Games Workshop Retailer Locator...")
        scraper = GamesWorkshopScraper()
        try:
            stores = scraper.fetch_stores(max_requests=max_requests)
        finally:
            scraper.close()

        console.print(f"Saving {len(stores)} stores to cache: {resolved_cache}")
        save_raw_to_cache(stores, resolved_cache)

    assert isinstance(stores, list), "stores must be a list"
    assert len(stores) <= _MAX_CLI_STORES, f"Store count {len(stores)} exceeds cap"

    # Stats
    us_stores = [s for s in stores if s.country.upper() == "US"]
    store_types: dict[str, int] = {}
    for s in stores:
        st = s.store_type or "unknown"
        store_types[st] = store_types.get(st, 0) + 1

    console.print("\n[bold]Games Workshop Discovery Results:[/bold]")
    console.print(f"  Total found:  {len(stores)}")
    console.print(f"  US stores:    {len(us_stores)}")
    for stype, count in sorted(store_types.items(), key=lambda x: -x[1]):
        console.print(f"  {stype}: {count}")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes written to database.[/yellow]")
        return

    console.print("\nIngesting into database...")
    with get_session() as session:
        report = ingest_gw_stores(stores, session)

    console.print(f"\n[green]{report}[/green]")
    if report.errors > 0:
        console.print(f"\n[yellow]Errors ({report.errors}):[/yellow]")
        for detail in report.error_details[:20]:
            console.print(f"  - {detail}")
        if report.errors > 20:
            console.print(f"  ... and {report.errors - 20} more")


_DEFAULT_COMIC_CACHE_PATH = Path("data/comic_stores_raw.json")


@discover.command(name="comics")
@click.option(
    "--cache-file",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to save/load raw comic store data (JSON).",
)
@click.option("--dry-run", is_flag=True, default=False, help="Show stats without writing.")
@click.option("--from-cache", is_flag=True, default=False, help="Load from cache file.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
@click.option(
    "--max-requests",
    type=int,
    default=None,
    help="Max API requests (limits scraping).",
)
def comics(
    cache_file: Path | None,
    dry_run: bool,
    from_cache: bool,
    verbose: bool,
    max_requests: int | None,
) -> None:
    """Fetch and ingest stores from comic book store directories."""
    from lgs_directory.discovery.comic_stores import (
        ComicStoreRaw,
        ComicStoreScraper,
        load_raw_from_cache,
        save_raw_to_cache,
    )
    from lgs_directory.discovery.ingest_comic import ingest_comic_stores

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    resolved_cache = cache_file or _DEFAULT_COMIC_CACHE_PATH
    assert isinstance(resolved_cache, Path)

    stores: list[ComicStoreRaw]

    if from_cache:
        if not resolved_cache.exists():
            console.print(f"[red]Cache file not found:[/red] {resolved_cache}")
            raise SystemExit(1)
        console.print(f"Loading from cache: {resolved_cache}")
        stores = load_raw_from_cache(resolved_cache)
    else:
        from lgs_directory.config import get_settings as _get_comic_settings

        settings = _get_comic_settings()
        if not settings.google_places_api_key:
            console.print("[red]GOOGLE_PLACES_API_KEY not set in environment[/red]")
            raise SystemExit(1)

        console.print("Fetching comic stores via Google Places Text Search...")
        scraper = ComicStoreScraper(api_key=settings.google_places_api_key)
        try:
            stores = scraper.fetch_stores(max_requests=max_requests)
        finally:
            scraper.close()

        console.print(f"Saving {len(stores)} stores to cache: {resolved_cache}")
        save_raw_to_cache(stores, resolved_cache)

    assert isinstance(stores, list), "stores must be a list"
    assert len(stores) <= _MAX_CLI_STORES, f"Store count {len(stores)} exceeds cap"
    with_website = sum(1 for s in stores if s.website)
    with_phone = sum(1 for s in stores if s.phone)

    console.print("\n[bold]Comic Store Discovery Results:[/bold]")
    console.print(f"  Total found:  {len(stores)}")
    console.print(f"  With website: {with_website}")
    console.print(f"  With phone:   {with_phone}")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes written to database.[/yellow]")
        return

    console.print("\nIngesting into database...")
    with get_session() as session:
        report = ingest_comic_stores(stores, session)

    console.print(f"\n[green]{report}[/green]")
    if report.errors > 0:
        console.print(f"\n[yellow]Errors ({report.errors}):[/yellow]")
        for detail in report.error_details[:20]:
            console.print(f"  - {detail}")
        if report.errors > 20:
            console.print(f"  ... and {report.errors - 20} more")


@discover.command("auto-categorize")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
def auto_categorize(verbose: bool) -> None:
    """Auto-assign categories based on website content products."""
    from lgs_directory.discovery.auto_categorize import auto_categorize_from_content

    assert isinstance(verbose, bool), "verbose must be a bool"

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    with get_session() as session:
        processed, assigned = auto_categorize_from_content(session)

    assert isinstance(processed, int), "processed must be an int"
    assert isinstance(assigned, int), "assigned must be an int"

    console.print("\n[bold]Auto-Categorization Results:[/bold]")
    console.print(f"  Stores processed:    {processed}")
    console.print(f"  Categories assigned: {assigned}")


_DEFAULT_RETRO_CACHE_PATH = Path("data/retro_games_raw.json")


@discover.command(name="retro-games")
@click.option(
    "--cache-file",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to save/load raw retro game store data (JSON).",
)
@click.option("--dry-run", is_flag=True, default=False, help="Show stats without writing.")
@click.option("--from-cache", is_flag=True, default=False, help="Load from cache file.")
@click.option("--verbose", is_flag=True, default=False, help="Enable verbose logging.")
@click.option(
    "--max-requests",
    type=int,
    default=None,
    help="Max API requests (limits scraping).",
)
def retro_games(
    cache_file: Path | None,
    dry_run: bool,
    from_cache: bool,
    verbose: bool,
    max_requests: int | None,
) -> None:
    """Fetch and ingest stores from retro game store directories."""
    from lgs_directory.discovery.ingest_retro import ingest_retro_stores
    from lgs_directory.discovery.retro_games import (
        RetroGameScraper,
        RetroGameStoreRaw,
        load_raw_from_cache,
        save_raw_to_cache,
    )

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    resolved_cache = cache_file or _DEFAULT_RETRO_CACHE_PATH
    assert isinstance(resolved_cache, Path)

    stores: list[RetroGameStoreRaw]

    if from_cache:
        if not resolved_cache.exists():
            console.print(f"[red]Cache file not found:[/red] {resolved_cache}")
            raise SystemExit(1)
        console.print(f"Loading from cache: {resolved_cache}")
        stores = load_raw_from_cache(resolved_cache)
    else:
        from lgs_directory.config import get_settings as _get_retro_settings

        settings = _get_retro_settings()
        if not settings.google_places_api_key:
            console.print("[red]GOOGLE_PLACES_API_KEY not set in environment[/red]")
            raise SystemExit(1)

        console.print("Fetching retro game stores via Google Places Text Search...")
        scraper = RetroGameScraper(api_key=settings.google_places_api_key)
        try:
            stores = scraper.fetch_stores(max_requests=max_requests)
        finally:
            scraper.close()

        console.print(f"Saving {len(stores)} stores to cache: {resolved_cache}")
        save_raw_to_cache(stores, resolved_cache)

    assert isinstance(stores, list), "stores must be a list"
    assert len(stores) <= _MAX_CLI_STORES, f"Store count {len(stores)} exceeds cap"
    with_website = sum(1 for s in stores if s.website)
    with_phone = sum(1 for s in stores if s.phone)

    console.print("\n[bold]Retro Game Store Discovery Results:[/bold]")
    console.print(f"  Total found:  {len(stores)}")
    console.print(f"  With website: {with_website}")
    console.print(f"  With phone:   {with_phone}")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes written to database.[/yellow]")
        return

    console.print("\nIngesting into database...")
    with get_session() as session:
        report = ingest_retro_stores(stores, session)

    console.print(f"\n[green]{report}[/green]")
    if report.errors > 0:
        console.print(f"\n[yellow]Errors ({report.errors}):[/yellow]")
        for detail in report.error_details[:20]:
            console.print(f"  - {detail}")
        if report.errors > 20:
            console.print(f"  ... and {report.errors - 20} more")


# ---------------------------------------------------------------------------
# OSM-state discovery (kumi Overpass mirror, per-state cadence)
# ---------------------------------------------------------------------------


@discover.command(name="osm-state")
@click.option(
    "--state",
    type=str,
    default=None,
    help="Process a single 2-letter US state code (e.g. CO).",
)
@click.option(
    "--next",
    "use_next",
    is_flag=True,
    default=False,
    help="Read the rotation cursor and process the next state, then advance.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Fetch + classify but do not write to the database.",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Print per-candidate decisions to stderr.",
)
@click.option(
    "--max-candidates",
    type=int,
    default=None,
    help="Defensive cap on processed candidates (testing only).",
)
def osm_state(
    state: str | None,
    use_next: bool,
    dry_run: bool,
    verbose: bool,
    max_candidates: int | None,
) -> None:
    """Discover LGS via OpenStreetMap Overpass for one US state."""
    from lgs_directory.discovery.ingest_osm import ingest_osm_state
    from lgs_directory.discovery.osm_overpass import OverpassClient
    from lgs_directory.discovery.osm_state_queue import (
        advance_cursor,
        normalize_state_code,
        peek_next_state,
    )

    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if state is None and not use_next:
        console.print("[red]One of --state or --next is required[/red]")
        raise SystemExit(1)
    if state is not None and use_next:
        console.print("[red]--state and --next are mutually exclusive[/red]")
        raise SystemExit(1)

    if use_next:
        target_state = peek_next_state()
        console.print(
            f"[dim]Cursor head: [/dim]"
            f"[bold]{target_state}[/bold]"
            f"[dim] (use --state to override)[/dim]"
        )
    else:
        assert state is not None
        try:
            target_state = normalize_state_code(state)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise SystemExit(1) from exc

    console.print(f"Fetching OSM Overpass for state=[bold]{target_state}[/bold]...")
    client = OverpassClient()
    try:
        raw_places = client.fetch_state(target_state)
    finally:
        client.close()

    fetch_stats = client.last_fetch_stats
    if max_candidates is not None and max_candidates >= 0:
        raw_places = raw_places[:max_candidates]

    console.print(
        f"  Overpass elapsed: {fetch_stats.elapsed_secs:.2f}s "
        f"(fallback={'yes' if fetch_stats.fallback_used else 'no'})"
    )
    console.print(
        f"  Raw elements: {fetch_stats.raw_elements}, "
        f"parsed candidates: {fetch_stats.parsed}, "
        f"skipped no-name: {fetch_stats.skipped_no_name}"
    )

    if dry_run:
        with get_session() as session:
            report = ingest_osm_state(
                target_state, raw_places, session, dry_run=True,
            )
            session.rollback()
    else:
        with get_session() as session:
            report = ingest_osm_state(
                target_state, raw_places, session, dry_run=False,
            )
            session.commit()

    table = Table(title=f"OSM[{target_state}] Ingest Summary")
    table.add_column("Metric")
    table.add_column("Count", justify="right")
    table.add_row("Fetched", str(report.fetched))
    table.add_row("AUTO_ACCEPT", str(report.auto_accept))
    table.add_row("CANDIDATE_QUEUE", str(report.candidate_queue))
    table.add_row("AUTO_REJECT", str(report.auto_reject))
    table.add_row("Inserted as candidate", str(report.inserted_candidate))
    table.add_row("Inserted as pending_review", str(report.inserted_pending_review))
    table.add_row("Augmented existing", str(report.augmented_existing))
    table.add_row("Match (no change)", str(report.skipped_no_change))
    table.add_row("Skipped (no address)", str(report.skipped_no_address))
    table.add_row("Errors", str(report.errors))
    console.print(table)

    if dry_run:
        console.print("[yellow]Dry run — no DB writes.[/yellow]")
    else:
        if use_next:
            new_cursor = advance_cursor(target_state)
            next_state = peek_next_state()
            console.print(
                f"[green]Cursor advanced[/green]: "
                f"index={new_cursor.next_index} next={next_state}"
            )

    if verbose and report.sample_decisions:
        console.print("\n[bold]Sample decisions[/bold]")
        sample_cap = min(len(report.sample_decisions), 200)
        for i in range(sample_cap):
            console.print(f"  {report.sample_decisions[i]}")

    # Advisory anomaly threshold (per Chris's decision: advisory only).
    if report.fetched >= 50:
        accept_rate = report.auto_accept / report.fetched
        reject_rate = report.auto_reject / report.fetched
        if accept_rate < 0.20:
            console.print(
                f"[yellow]ADVISORY: low AUTO_ACCEPT rate ({accept_rate:.1%}) — "
                "filter may be too strict.[/yellow]"
            )
        if reject_rate > 0.70:
            console.print(
                f"[yellow]ADVISORY: high AUTO_REJECT rate ({reject_rate:.1%}) — "
                "tag set may be too permissive.[/yellow]"
            )

    if report.errors > 0:
        console.print(f"\n[yellow]Errors ({report.errors}):[/yellow]")
        cap = min(report.errors, 20)
        for i in range(cap):
            console.print(f"  - {report.error_details[i]}")


@discover.command(name="review-queue")
@click.option(
    "--limit",
    type=int,
    default=20,
    show_default=True,
    help="Max number of pending_review stores to show.",
)
def review_queue(limit: int) -> None:
    """List PENDING_REVIEW stores for manual promotion / rejection."""
    from lgs_directory.discovery.ingest_osm import (
        find_osm_external_ref,
        list_pending_review_stores,
    )

    if limit <= 0:
        console.print("[red]--limit must be a positive integer[/red]")
        raise SystemExit(1)

    bounded_limit = min(limit, 1000)
    with get_session() as session:
        stores = list_pending_review_stores(session, limit=bounded_limit)
        if not stores:
            console.print("[green]No pending_review stores.[/green]")
            return

        table = Table(title=f"Pending Review Queue (showing {len(stores)})")
        table.add_column("ID", overflow="fold")
        table.add_column("Name")
        table.add_column("City")
        table.add_column("State")
        table.add_column("OSM ID")
        table.add_column("First Seen")
        scan = min(len(stores), bounded_limit)
        for i in range(scan):
            store = stores[i]
            addr = store.address or {}
            ref = find_osm_external_ref(str(store.id), session)
            osm_id = ref.external_id if ref is not None else "—"
            first_seen = (
                store.first_seen.isoformat() if store.first_seen else "—"
            )
            table.add_row(
                str(store.id),
                store.name,
                str(addr.get("city", "")),
                str(addr.get("state", "")),
                osm_id,
                first_seen,
            )
        console.print(table)
        console.print(
            "\n[dim]To promote: update status via SQL "
            "(`UPDATE stores SET status='candidate' WHERE id='...';`).[/dim]"
        )
