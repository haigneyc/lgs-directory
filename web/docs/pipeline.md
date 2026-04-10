# Roll For Store — Data Pipeline

The Python pipeline lives at the repo root (not in `web/`). It feeds the PostgreSQL database that the web app reads.

## Pipeline Overview

```
Discover → Normalize → Dedup → Ingest → Enrich → Scrape
```

## Discovery Sources

### WPN (Wizards Play Network)

`lgs discover wpn` — fetches store list from the WPN Store Locator. Uses Playwright to harvest Akamai cookies if needed. Stores from WPN are the highest-trust source (WPN registration is a trust signal).

### Google Places API

`lgs discover google` — grid scan of the US using Google Places API. Finds stores via search terms (tabletop games, card games, game store, etc.). Results enter as `candidate` status.

### Comic Stores

`lgs discover comics` — discovers comic book shops via a separate source. These enter with `category = 'comic_shop'`.

### Retro Games

`lgs discover retro` — discovers retro video game stores.

### Games Workshop

`lgs discover games-workshop` — hits the official GW store locator. Stores found here get a `store_external_refs` row with `provider = 'games_workshop'`, which satisfies the trust filter.

## Normalization and Dedup

After discovery, records are normalized to the internal schema (phone format, address components, category inference) and fuzzy-deduped against existing records before ingest.

Key module: `src/lgs_directory/discovery/normalize.py`, `dedup.py`.

## Enrichment

`lgs enrich [store-id]` — enriches individual stores with additional data:
- Online presence detection (website scraping)
- Platform detection (Shopify, WooCommerce, etc.)
- Product catalog sampling

## Content Scraping

`lgs scrape [store-id]` — scrapes store website for product keywords. Results go into `store_external_refs` with `provider = 'website_content'` and a `products` array in the payload. Non-empty `products` satisfies the trust filter for candidates.

## CLI Reference

Full CLI documentation: [../../docs/cli_reference.md](../../docs/cli_reference.md)

## Key Files

| File | Purpose |
|------|---------|
| `src/lgs_directory/cli/main.py` | CLI entry point |
| `src/lgs_directory/discovery/wpn.py` | WPN scraper |
| `src/lgs_directory/discovery/google_places.py` | Google Places grid scan |
| `src/lgs_directory/discovery/ingest.py` | Database upsert logic |
| `src/lgs_directory/discovery/dedup.py` | Fuzzy deduplication |
| `src/lgs_directory/discovery/quality_filters.py` | Candidate quality filters |
| `src/lgs_directory/discovery/trust_score.py` | Trust scoring logic |
| `src/lgs_directory/models/` | SQLAlchemy ORM models |
| `alembic/` | Database migration files |

## Development Commands

```bash
# Set up Python environment (repo root)
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
lgs --help

# Run discovery
lgs discover wpn
lgs discover google
lgs discover status

# Run migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Tests + lint
pytest
ruff check src/ tests/
mypy src/
```

## Product Requirements

Full PRD: [../../docs/prd.md](../../docs/prd.md)
Phase 2 PRD: [../../docs/phase2_prd.md](../../docs/phase2_prd.md)
