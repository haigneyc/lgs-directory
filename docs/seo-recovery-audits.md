# SEO Recovery Audit Scripts

These tools are read-only except `scripts/backfill_store_slugs.py`. None of them call Google Places APIs.

## Deploy Slug Guard Migration

Point Alembic at the target database, preferably the direct migration URL rather than the pooled app URL:

```bash
MIGRATION_DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require" \
  uv run alembic upgrade head
```

`alembic/env.py` prefers `MIGRATION_DATABASE_URL` and falls back to `DATABASE_URL`. The new guard migration adds a `NOT VALID` check constraint, so existing dirty rows are allowed temporarily, but new or updated public `active`, `verified`, or `candidate` rows must have a non-empty slug.

## Backfill Existing Slugless Rows

Preview the writes first:

```bash
DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require" \
  uv run python scripts/backfill_store_slugs.py --dry-run
```

Apply the backfill:

```bash
DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require" \
  uv run python scripts/backfill_store_slugs.py
```

The script only updates rows where `stores.slug` is missing and uses the shared Python slug helper.

## Daily Slugless Health Check

```bash
DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require" \
  uv run python scripts/check_public_slugless_stores.py
```

Expected result: `OK: no public slugless stores found`. Nonzero exit means a public `active`, `verified`, or `candidate` row has `slug IS NULL` or an empty slug.

## Public Store Quality Audit

```bash
DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require" \
  uv run python scripts/audit_public_store_quality.py \
  > public-store-quality.csv
```

Optional GSC prioritization uses the Performance > Search results > Pages CSV:

```bash
DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require" \
  uv run python scripts/audit_public_store_quality.py \
  --gsc-pages-csv ~/Downloads/gsc-pages.csv \
  > public-store-quality.csv
```

Buckets are `keep`, `suspect_noindex`, and `remove_or_pending_review`.

## GSC Non-Indexed Bucket Audit

Download these exact CSV exports from Google Search Console, then pass one or more files to the script:

- Indexing > Pages > Crawled - currently not indexed > Export > CSV
- Indexing > Pages > Discovered - currently not indexed > Export > CSV
- Indexing > Pages > Duplicate without user-selected canonical > Export > CSV
- Performance > Search results > Pages tab > Export > CSV, for optional prioritization in the public store quality audit only

Run with the actual downloaded filenames:

```bash
uv run python scripts/audit_gsc_nonindexed_buckets.py \
  /path/to/crawled-not-indexed.csv \
  /path/to/discovered-not-indexed.csv \
  /path/to/duplicate-without-user-selected-canonical.csv \
  > gsc-nonindexed-buckets.csv
```

Output includes URL type counts, samples, likely cause, expected indexability, and recovery action.
