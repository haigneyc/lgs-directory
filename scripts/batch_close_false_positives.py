#!/usr/bin/env python3
"""Batch-close false-positive stores identified by Petra's 2026-04-06 audit.

Usage:
    python scripts/batch_close_false_positives.py [--dry-run]

Closes all stores Petra flagged as false positives across Eagle Pass TX,
Homestead FL, Miami FL, and the Retro Games / Comics / Warhammer pages.
"""

from __future__ import annotations

import click
from sqlalchemy import func, select

from lgs_directory.db import get_session
from lgs_directory.models.enums import StoreStatus
from lgs_directory.models.store import Store

# Maximum number of stores we expect to close in one batch (safety cap)
_MAX_CLOSE_COUNT = 200

# Store IDs to close — from Petra's false positive report 2026-04-06
_STORES_TO_CLOSE: list[str] = [
    # --- Eagle Pass, TX ---
    "739254ec-359a-492a-b8da-8b641294144b",  # 210 Armory (gun shop)
    # Academy Sports, Casino Grocery, Doobie's Hemp, G Wireless,
    # Kickapoo Casino Hotel, Kickapoo Convenience, Mall de las Aguilas,
    # Sparkly Girls — these are google_places entries without store URLs
    # so we identify them by name below via a separate query

    # --- Homestead, FL ---
    "c940065a-8a5c-4478-a9c3-ce09c6c31fb5",  # American Armory (gun shop)
    "89db22b3-989a-469b-a991-5070a7e1e6db",  # Arsenal Arms Inc (gun shop)
    "8bc9f521-79fe-4274-826f-c057acb8d794",  # Coastal Crafts
    "111ec238-5913-4a67-aaf3-eec4843b4070",  # Don Stitch Embroidery
    "c9bb39eb-da3e-42e4-9453-7a2af588cce8",  # Fit Family Club (fitness)
    "10009c0c-644e-4005-ae42-50b60381793d",  # Flogrown service Gun Shop
    "e60cf60d-fb19-412c-87ab-d128016e00af",  # Florida Armory Gun Shop
    "67f6ae31-648f-43b6-8e18-7d5ba0e023d4",  # Fun Games Kiddie Park
    "4142ac94-1dfe-45cf-bcf7-54a79a287a14",  # Homestead Trading Post Guns
    "f760135e-2128-44a6-8d2c-52766b23395a",  # Master Graphicz
    "4d345b11-83dd-442f-b9c8-5f5e8a288ae9",  # Michaels (craft chain)
    "6af5f14a-973a-46b3-8490-c8178d2fc5e9",  # Naranja Trading Post & Pawn
    "18e9ae2f-a8e6-41a5-8e09-c380da229422",  # Nunez Electronics
    "d05f13ed-0fec-4dad-8b7d-a555257a1a15",  # RieRie's Creations
    "f27cee9b-6a2f-4001-87e4-86144e513607",  # Sinar's Embroidery

    # --- Miami, FL ---
    # Barnes & Noble, Best Buy, Hobby Lobby, Michaels — chain names
    # will be caught by blocklist going forward; close specific IDs
    # if we can find them. For now, close the ones with explicit URLs:
    # (Petra did not provide individual store URLs for all Miami entries,
    # only category observations. We close the ones we can identify.)

    # --- Retro Games / NY cluster ---
    # These were observed on category pages; Petra didn't provide individual
    # store page URLs. We'll use name-based lookup below for these.

    # --- Warhammer ---
    # 3RD UNIVERSE CONSULTING — consulting firm (borderline, close it)
]

# Names to look up and close (stores without explicit UUIDs in the report)
_NAMES_TO_CLOSE: list[tuple[str, str, str]] = [
    # (name_fragment, city, state) — case-insensitive ILIKE match
    # Eagle Pass, TX
    ("Academy Sports", "Eagle Pass", "TX"),
    ("Casino Grocery", "Eagle Pass", "TX"),
    ("Doobie's Hemp", "Eagle Pass", "TX"),
    ("G Wireless", "Eagle Pass", "TX"),
    ("Kickapoo Lucky Eagle Casino Hotel", "Eagle Pass", "TX"),
    ("Kickapoo Lucky Eagle Convenience", "Eagle Pass", "TX"),
    ("Mall de las Aguilas", "Eagle Pass", "TX"),
    ("Sparkly Girls", "Eagle Pass", "TX"),
    # Miami, FL — chain stores and specific false positives
    ("CW Gunwerks", "Miami", "FL"),
    ("Crafters Lab", "Miami", "FL"),
    ("Jenly Wholesale", "Miami", "FL"),
    ("Miami Computers", "Miami", "FL"),
    ("Star Games Parts & Electronics", "Miami", "FL"),
    ("Stone Hart's Gun Club", "Miami", "FL"),
    ("TONY'S ART & FRAMING", "Miami", "FL"),
    ("Shops of Kendall", "Miami", "FL"),
    ("The Fishing Game", "Miami", "FL"),
    # Retro Games / NY cluster
    ("All My Friends Books", "Cortland", "NY"),
    ("Altenew", "Syracuse", "NY"),
    ("Berry Hill Book Shop", "Deansboro", "NY"),
    ("Books & Melodies", "Syracuse", "NY"),
    ("Books End", "Syracuse", "NY"),
    ("Bullseye Coins & Currency", "North Syracuse", "NY"),
    ("Butter-nut Sport Shop", "Minoa", "NY"),
    ("Butternut Creek Armory", "Jamesville", "NY"),
    ("Cell Phones For Less", "Syracuse", "NY"),
    # Warhammer
    ("3RD UNIVERSE CONSULTING", "Croton on Hudson", "NY"),
]

_EXPECTED_ID_COUNT = 16
_MAX_NAME_LOOKUPS = 50


@click.command()
@click.option("--dry-run", is_flag=True, default=False, help="Show what would happen.")
def main(dry_run: bool) -> None:
    """Batch-close false-positive stores from Petra's 2026-04-06 report."""
    assert len(_STORES_TO_CLOSE) == _EXPECTED_ID_COUNT, (
        f"Expected {_EXPECTED_ID_COUNT} store IDs, got {len(_STORES_TO_CLOSE)}"
    )
    assert len(_NAMES_TO_CLOSE) <= _MAX_NAME_LOOKUPS, "Too many name lookups"

    closed_count = 0
    skipped_count = 0
    missing_count = 0

    with get_session() as session:
        # --- Phase 1: Close by explicit UUID ---
        click.echo("=== Phase 1: Closing by store ID ===")
        for idx, store_id in enumerate(_STORES_TO_CLOSE):
            if idx >= _MAX_CLOSE_COUNT:
                break

            stmt = select(Store).where(Store.id == store_id).limit(1)
            store = session.execute(stmt).scalar_one_or_none()

            if store is None:
                click.echo(f"  MISSING: {store_id}")
                missing_count += 1
                continue

            assert isinstance(store, Store), "query result must be a Store"

            if store.status == StoreStatus.CLOSED:
                click.echo(f"  SKIP (already closed): {store.name}")
                skipped_count += 1
                continue

            if dry_run:
                click.echo(f"  [DRY RUN] Would close: {store.name} ({store_id})")
                closed_count += 1
                continue

            old_status = store.status
            store.status = StoreStatus.CLOSED
            note_text = "\nMarked closed: false positive (Petra audit 2026-04-06)."
            store.notes = (store.notes or "") + note_text

            assert store.status == StoreStatus.CLOSED
            click.echo(f"  CLOSED: {store.name} ({old_status} -> closed)")
            closed_count += 1

        # --- Phase 2: Close by name + city + state lookup ---
        click.echo("\n=== Phase 2: Closing by name lookup ===")
        for idx, (name_frag, city, state) in enumerate(_NAMES_TO_CLOSE):
            if idx >= _MAX_NAME_LOOKUPS:
                break

            stmt = (
                select(Store)
                .where(
                    Store.name.ilike(f"%{name_frag}%"),
                    Store.status != StoreStatus.CLOSED,
                )
                .limit(5)
            )
            stores = session.execute(stmt).scalars().all()

            if len(stores) == 0:
                click.echo(f"  NOT FOUND: {name_frag} ({city}, {state})")
                missing_count += 1
                continue

            for store in stores:
                assert isinstance(store, Store), "query result must be a Store"

                store_city = (store.address or {}).get("city", "")
                store_state = (store.address or {}).get("state", "")

                if store_city.upper() != city.upper():
                    continue
                if store_state.upper() != state.upper():
                    continue

                if dry_run:
                    click.echo(
                        f"  [DRY RUN] Would close: {store.name} "
                        f"({store_city}, {store_state})"
                    )
                    closed_count += 1
                    continue

                old_status = store.status
                store.status = StoreStatus.CLOSED
                note_text = "\nMarked closed: false positive (Petra audit 2026-04-06)."
                store.notes = (store.notes or "") + note_text

                assert store.status == StoreStatus.CLOSED
                click.echo(
                    f"  CLOSED: {store.name} ({old_status} -> closed) "
                    f"[{store_city}, {store_state}]"
                )
                closed_count += 1

        if dry_run:
            click.echo(f"\n[DRY RUN] Would close {closed_count} stores.")
            click.echo(f"Not found / missing: {missing_count}")
            session.rollback()
            return

        # Summary
        total_closed_stmt = (
            select(func.count())
            .select_from(Store)
            .where(Store.status == StoreStatus.CLOSED)
        )
        total_closed = session.execute(total_closed_stmt).scalar_one()
        assert isinstance(total_closed, int), "count must be an integer"

        click.echo(f"\nClosed {closed_count} stores.")
        click.echo(f"Skipped (already closed): {skipped_count}")
        click.echo(f"Not found / missing: {missing_count}")
        click.echo(f"Total closed stores in DB: {total_closed}")


if __name__ == "__main__":
    main()
