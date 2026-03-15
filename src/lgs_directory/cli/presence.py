"""CLI commands for managing online presences."""

from __future__ import annotations

from uuid import UUID

import click
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from lgs_directory.db import get_session
from lgs_directory.models.enums import ChannelType, Platform, PresenceStatus
from lgs_directory.models.online_presence import OnlinePresence
from lgs_directory.models.store import Store

console = Console()


@click.group()
def presence() -> None:
    """Manage online presences for stores."""


@presence.command()
@click.argument("store_id", type=click.UUID)
@click.option(
    "--channel",
    required=True,
    type=click.Choice([c.value for c in ChannelType], case_sensitive=False),
    help="Channel type",
)
@click.option("--url", required=True, help="URL of the online presence")
@click.option(
    "--platform",
    type=click.Choice([p.value for p in Platform], case_sensitive=False),
    default=None,
    help="E-commerce platform",
)
def add(store_id: UUID, channel: str, url: str, platform: str | None) -> None:
    """Add an online presence to a store."""
    assert url, "URL must not be empty"

    with get_session() as session:
        store = session.get(Store, store_id)
        if store is None:
            console.print(f"[red]Store not found:[/red] {store_id}")
            raise SystemExit(1)

        assert store.id is not None

        new_presence = OnlinePresence(
            store_id=store.id,
            channel_type=ChannelType(channel),
            url=url,
            platform=Platform(platform) if platform else None,
            status=PresenceStatus.ACTIVE,
        )
        session.add(new_presence)
        session.flush()
        assert new_presence.id is not None, "Presence ID was not generated"
        presence_id = new_presence.id

    console.print(f"[green]Created presence:[/green] {channel} -> {url} (id={presence_id})")


@presence.command("list")
@click.argument("store_id", type=click.UUID)
def list_presences(store_id: UUID) -> None:
    """List online presences for a store."""
    with get_session() as session:
        store = session.get(Store, store_id)
        if store is None:
            console.print(f"[red]Store not found:[/red] {store_id}")
            raise SystemExit(1)

        stmt = select(OnlinePresence).where(OnlinePresence.store_id == store_id)
        presences = list(session.execute(stmt).scalars().all())

    if not presences:
        console.print("[yellow]No presences found for this store.[/yellow]")
        return

    table = Table(title=f"Online Presences for {store.name}")
    table.add_column("ID", style="dim", max_width=36)
    table.add_column("Channel")
    table.add_column("URL", max_width=60)
    table.add_column("Platform")
    table.add_column("Singles?")
    table.add_column("Status")

    for p in presences:
        table.add_row(
            str(p.id),
            p.channel_type,
            p.url,
            p.platform or "-",
            str(p.sells_mtg_singles) if p.sells_mtg_singles is not None else "-",
            p.status,
        )

    console.print(table)


@presence.command()
@click.argument("presence_id", type=click.UUID)
@click.option("--url", default=None, help="New URL")
@click.option(
    "--platform",
    type=click.Choice([p.value for p in Platform], case_sensitive=False),
    default=None,
    help="New platform",
)
@click.option("--sells-singles/--no-sells-singles", default=None, help="Sells MTG singles?")
@click.option(
    "--status",
    type=click.Choice([s.value for s in PresenceStatus], case_sensitive=False),
    default=None,
    help="New status",
)
def edit(
    presence_id: UUID,
    url: str | None,
    platform: str | None,
    sells_singles: bool | None,
    status: str | None,
) -> None:
    """Edit an online presence."""
    if all(v is None for v in (url, platform, sells_singles, status)):
        console.print(
            "[yellow]No changes specified. "
            "Use --url, --platform, --sells-singles, or --status.[/yellow]"
        )
        return

    with get_session() as session:
        p = session.get(OnlinePresence, presence_id)
        if p is None:
            console.print(f"[red]Presence not found:[/red] {presence_id}")
            raise SystemExit(1)

        if url is not None:
            assert url, "URL must not be empty"
            p.url = url
        if platform is not None:
            p.platform = Platform(platform)
        if sells_singles is not None:
            p.sells_mtg_singles = sells_singles
        if status is not None:
            p.status = PresenceStatus(status)

        session.flush()
        assert p.id is not None

    console.print(f"[green]Updated presence:[/green] {presence_id}")


@presence.command()
@click.argument("presence_id", type=click.UUID)
@click.option("--hard", is_flag=True, default=False, help="Permanently delete")
def remove(presence_id: UUID, hard: bool) -> None:
    """Remove an online presence (soft-delete by default)."""
    with get_session() as session:
        p = session.get(OnlinePresence, presence_id)
        if p is None:
            console.print(f"[red]Presence not found:[/red] {presence_id}")
            raise SystemExit(1)

        if hard:
            session.delete(p)
            console.print(f"[red]Deleted presence:[/red] {presence_id}")
        else:
            p.status = PresenceStatus.DEAD
            session.flush()
            assert p.id is not None
            console.print(f"[yellow]Soft-deleted presence (status=dead):[/yellow] {presence_id}")
