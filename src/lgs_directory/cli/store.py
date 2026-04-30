"""CLI commands for managing stores."""

from __future__ import annotations

from uuid import UUID

import click
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from lgs_directory.db import get_session
from lgs_directory.models.enums import DiscoverySource, StoreStatus, WpnLevel
from lgs_directory.models.store import Store
from lgs_directory.schemas import AddressSchema
from lgs_directory.slug import ensure_public_store_slug

console = Console()

MAX_LIST_LIMIT = 500
DEFAULT_LIST_LIMIT = 50


@click.group()
def store() -> None:
    """Manage stores in the directory."""


@store.command()
@click.option("--name", required=True, help="Store name")
@click.option("--street", required=True, help="Street address")
@click.option("--city", required=True, help="City")
@click.option("--state", required=True, help="Two-letter state code (e.g. CA)")
@click.option("--zip", "zip_code", required=True, help="ZIP code")
@click.option("--phone", default=None, help="Phone number")
@click.option(
    "--source",
    type=click.Choice([s.value for s in DiscoverySource], case_sensitive=False),
    default=DiscoverySource.MANUAL.value,
    help="Discovery source",
)
@click.option("--wpn-id", default=None, help="WPN identifier")
@click.option(
    "--wpn-level",
    type=click.Choice([w.value for w in WpnLevel], case_sensitive=False),
    default=None,
    help="WPN level",
)
def add(
    name: str,
    street: str,
    city: str,
    state: str,
    zip_code: str,
    phone: str | None,
    source: str,
    wpn_id: str | None,
    wpn_level: str | None,
) -> None:
    """Add a new store to the directory."""
    assert name, "Name must not be empty"

    try:
        addr = AddressSchema(street=street, city=city, state=state.upper(), zip_code=zip_code)
    except ValidationError as exc:
        console.print(f"[red]Invalid address:[/red] {exc}")
        raise SystemExit(1) from exc

    new_store = Store(
        name=name,
        address=addr.model_dump(),
        phone=phone,
        status=StoreStatus.CANDIDATE,
        discovery_source=DiscoverySource(source),
        wpn_id=wpn_id,
        wpn_level=WpnLevel(wpn_level) if wpn_level else None,
    )

    with get_session() as session:
        ensure_public_store_slug(new_store, session)
        session.add(new_store)
        session.flush()
        assert new_store.id is not None, "Store ID was not generated"
        store_id = new_store.id

    console.print(f"[green]Created store:[/green] {name} (id={store_id})")


@store.command("list")
@click.option(
    "--status",
    type=click.Choice([s.value for s in StoreStatus], case_sensitive=False),
    default=None,
    help="Filter by status",
)
@click.option("--state", "state_filter", default=None, help="Filter by state code")
@click.option(
    "--source",
    type=click.Choice([s.value for s in DiscoverySource], case_sensitive=False),
    default=None,
    help="Filter by discovery source",
)
@click.option(
    "--limit",
    default=DEFAULT_LIST_LIMIT,
    type=click.IntRange(1, MAX_LIST_LIMIT),
    help=f"Max results (1-{MAX_LIST_LIMIT})",
)
def list_stores(
    status: str | None, state_filter: str | None, source: str | None, limit: int
) -> None:
    """List stores in the directory."""
    assert 1 <= limit <= MAX_LIST_LIMIT, f"Limit must be between 1 and {MAX_LIST_LIMIT}"

    stmt = select(Store)
    if status is not None:
        stmt = stmt.where(Store.status == status)
    if state_filter is not None:
        stmt = stmt.where(Store.address["state"].astext == state_filter.upper())
    if source is not None:
        stmt = stmt.where(Store.discovery_source == source)
    stmt = stmt.limit(limit)

    with get_session() as session:
        stores = list(session.execute(stmt).scalars().all())

    if not stores:
        console.print("[yellow]No stores found.[/yellow]")
        return

    table = Table(title=f"Stores ({len(stores)} results)")
    table.add_column("ID", style="dim", max_width=36)
    table.add_column("Name")
    table.add_column("City")
    table.add_column("State")
    table.add_column("Status")
    table.add_column("Source")

    for s in stores:
        assert s.address is not None
        table.add_row(
            str(s.id),
            s.name,
            s.address.get("city", ""),
            s.address.get("state", ""),
            s.status,
            s.discovery_source,
        )

    console.print(table)


@store.command()
@click.argument("store_id", type=click.UUID)
def show(store_id: UUID) -> None:
    """Show full details for a store."""
    with get_session() as session:
        s = session.get(Store, store_id)
        if s is None:
            console.print(f"[red]Store not found:[/red] {store_id}")
            raise SystemExit(1)

        assert s.address is not None

        console.print(f"\n[bold]{s.name}[/bold]")
        console.print(f"  ID:        {s.id}")
        console.print(f"  Status:    {s.status}")
        console.print(f"  Source:    {s.discovery_source}")
        console.print(f"  Address:   {s.address.get('street', '')}")
        city = s.address.get("city", "")
        st = s.address.get("state", "")
        zc = s.address.get("zip_code", "")
        console.print(f"             {city}, {st} {zc}")
        if s.phone:
            console.print(f"  Phone:     {s.phone}")
        if s.wpn_id:
            console.print(f"  WPN ID:    {s.wpn_id}")
        if s.wpn_level:
            console.print(f"  WPN Level: {s.wpn_level}")
        if s.latitude is not None and s.longitude is not None:
            console.print(f"  Lat/Lng:   {s.latitude}, {s.longitude}")
        console.print(f"  First seen:     {s.first_seen}")
        console.print(f"  Last validated: {s.last_validated or 'never'}")
        if s.notes:
            console.print(f"  Notes:     {s.notes}")

        # Show presences
        if s.presences:
            console.print(f"\n  [bold]Online Presences ({len(s.presences)}):[/bold]")
            for p in s.presences:
                console.print(f"    - [{p.status}] {p.channel_type}: {p.url}")
        else:
            console.print("\n  [dim]No online presences.[/dim]")

        console.print()


@store.command()
@click.argument("store_id", type=click.UUID)
@click.option("--name", default=None, help="New store name")
@click.option(
    "--status",
    type=click.Choice([s.value for s in StoreStatus], case_sensitive=False),
    default=None,
    help="New status",
)
@click.option("--phone", default=None, help="New phone number")
@click.option("--notes", default=None, help="Update notes")
def edit(
    store_id: UUID,
    name: str | None,
    status: str | None,
    phone: str | None,
    notes: str | None,
) -> None:
    """Edit an existing store."""
    if all(v is None for v in (name, status, phone, notes)):
        console.print(
            "[yellow]No changes specified. "
            "Use --name, --status, --phone, or --notes.[/yellow]"
        )
        return

    with get_session() as session:
        s = session.get(Store, store_id)
        if s is None:
            console.print(f"[red]Store not found:[/red] {store_id}")
            raise SystemExit(1)

        if name is not None:
            assert name, "Name must not be empty"
            s.name = name
        if status is not None:
            s.status = StoreStatus(status)
            ensure_public_store_slug(s, session)
        if phone is not None:
            s.phone = phone
        if notes is not None:
            s.notes = notes

        session.flush()
        assert s.id is not None

    console.print(f"[green]Updated store:[/green] {store_id}")
