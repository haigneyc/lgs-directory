#!/usr/bin/env python3
"""One-off script to mark a false-positive store as closed.

Usage:
    python scripts/mark_store_closed.py <store_id> [--dry-run]

This sets the store's status to 'closed' without deleting the row.
"""

from __future__ import annotations

import sys

import click
from sqlalchemy import select

from lgs_directory.db import get_session
from lgs_directory.models.enums import StoreStatus
from lgs_directory.models.store import Store


@click.command()
@click.argument("store_id", type=str)
@click.option("--dry-run", is_flag=True, default=False, help="Show what would happen.")
def main(store_id: str, dry_run: bool) -> None:
    """Mark a store as closed by its UUID."""
    assert isinstance(store_id, str), "store_id must be a string"
    assert len(store_id) > 0, "store_id must not be empty"

    with get_session() as session:
        stmt = select(Store).where(Store.id == store_id).limit(1)
        store = session.execute(stmt).scalar_one_or_none()

        if store is None:
            click.echo(f"ERROR: No store found with id={store_id}", err=True)
            sys.exit(1)

        assert isinstance(store, Store), "query result must be a Store"

        click.echo(f"Store:   {store.name}")
        click.echo(f"Status:  {store.status}")
        click.echo(f"Address: {store.address}")

        if store.status == StoreStatus.CLOSED:
            click.echo("Store is already closed. Nothing to do.")
            return

        if dry_run:
            click.echo(f"\n[DRY RUN] Would set status to 'closed' for: {store.name}")
            # Roll back so get_session's commit is a no-op
            session.rollback()
            return

        old_status = store.status
        store.status = StoreStatus.CLOSED
        store.notes = (store.notes or "") + "\nMarked closed: false positive (not a game store)."

        assert store.status == StoreStatus.CLOSED
        click.echo(f"\nUpdated: {old_status} -> {store.status}")
        click.echo("Done.")


if __name__ == "__main__":
    main()
