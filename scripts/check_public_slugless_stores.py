"""Fail if public/indexable stores are missing slugs.

Read-only health check for CI or daily cron:

    python3 scripts/check_public_slugless_stores.py
"""

from __future__ import annotations

from sqlalchemy import text

from lgs_directory.db import get_session

PUBLIC_STATUSES = ("active", "verified", "candidate")


def main() -> None:
    """Print grouped public slugless stores and exit nonzero on failures."""
    with get_session() as session:
        rows = session.execute(
            text(
                """
                SELECT status, discovery_source, count(*)::int AS count
                FROM stores
                WHERE status = ANY(:statuses)
                  AND (slug IS NULL OR btrim(slug) = '')
                GROUP BY status, discovery_source
                ORDER BY count DESC, status, discovery_source
                """
            ),
            {"statuses": list(PUBLIC_STATUSES)},
        ).mappings().all()

        samples = session.execute(
            text(
                """
                SELECT id::text AS id, name, status, discovery_source
                FROM stores
                WHERE status = ANY(:statuses)
                  AND (slug IS NULL OR btrim(slug) = '')
                ORDER BY first_seen DESC
                LIMIT 25
                """
            ),
            {"statuses": list(PUBLIC_STATUSES)},
        ).mappings().all()

    if len(rows) == 0:
        print("OK: no public slugless stores found")
        return

    print("FAIL: public slugless stores found")
    for row in rows:
        print(f"{row['status']}\t{row['discovery_source']}\t{row['count']}")

    print("\nSamples:")
    for row in samples:
        print(f"{row['id']}\t{row['status']}\t{row['discovery_source']}\t{row['name']}")

    raise SystemExit(1)


if __name__ == "__main__":
    main()
