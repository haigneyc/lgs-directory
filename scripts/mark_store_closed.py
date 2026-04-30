#!/usr/bin/env python3
"""One-off script to mark a store as closed.

Usage:
    python scripts/mark_store_closed.py <store_id> [--reason TEXT] [--source-url URL]
    python scripts/mark_store_closed.py <store_id> [--dry-run]

This sets the store's status to 'closed' without deleting the row.
"""

from __future__ import annotations

import sys

import click
from sqlalchemy import select

from lgs_directory.db import get_session
from lgs_directory.models.enums import CheckType, StoreStatus
from lgs_directory.models.store import Store
from lgs_directory.models.validation_log import ValidationLog


@click.command()
@click.argument("store_id", type=str)
@click.option("--dry-run", is_flag=True, default=False, help="Show what would happen.")
@click.option(
    "--reason",
    default="closure evidence",
    help="Human-readable reason for closing the store.",
)
@click.option("--source-url", default=None, help="Optional source URL for closure evidence.")
def main(store_id: str, dry_run: bool, reason: str, source_url: str | None) -> None:
    """Mark a store as closed by its UUID."""
    assert isinstance(store_id, str), "store_id must be a string"
    assert len(store_id) > 0, "store_id must not be empty"
    assert isinstance(reason, str) and len(reason.strip()) > 0

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
            click.echo(f"Reason: {reason}")
            if source_url:
                click.echo(f"Source: {source_url}")
            # Roll back so get_session's commit is a no-op
            session.rollback()
            return

        old_status = store.status
        store.status = StoreStatus.CLOSED
        note = f"\nMarked closed: {reason.strip()}."
        if source_url:
            note += f" Source: {source_url.strip()}"
        store.notes = (store.notes or "") + note
        session.add(ValidationLog(
            store_id=store.id,
            check_type=CheckType.CLOSURE_DETECT,
            result={
                "source": "mark_store_closed",
                "reason": reason.strip(),
                "source_url": source_url,
                "transition": f"{old_status} -> {StoreStatus.CLOSED.value}",
            },
        ))

        assert store.status == StoreStatus.CLOSED
        click.echo(f"\nUpdated: {old_status} -> {store.status}")
        click.echo("Done.")


if __name__ == "__main__":
    main()
