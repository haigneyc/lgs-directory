# CLI Reference

All commands are accessible via the `lgs` entry point.

## Discovery

### `lgs discover wpn`

Fetch and ingest stores from the WPN Store Locator. Automatically harvests Akamai cookies via Playwright if available.

```
lgs discover wpn [OPTIONS]

Options:
  --cache-file PATH   Save/load raw WPN data (default: data/wpn_raw.json)
  --dry-run           Fetch and show stats without writing to the database
  --from-cache        Load from cache file instead of fetching from API
  --verbose           Enable verbose logging
```

### `lgs discover google`

Fetch and ingest stores from Google Places API. Requires `GOOGLE_PLACES_API_KEY` in environment.

```
lgs discover google [OPTIONS]

Options:
  --cache-file PATH   Save/load raw Google Places data (default: data/google_places_raw.json)
  --dry-run           Show stats without writing to the database
  --from-cache        Load from cache file instead of fetching from API
  --verbose           Enable verbose logging
  --limit-cells INT   Limit grid cells to scan (for testing)
```

### `lgs discover status`

Show discovery statistics: total stores, by source, by status, WPN count.

```
lgs discover status
```

## Store Management

### `lgs store add`

Create a new store manually.

```
lgs store add --name NAME --street STREET --city CITY --state ST --zip ZIP [OPTIONS]

Options:
  --phone TEXT        Phone number
  --status TEXT       Initial status (default: candidate)
  --source TEXT       Discovery source (default: manual)
```

### `lgs store list`

List stores with optional filters.

```
lgs store list [OPTIONS]

Options:
  --status TEXT       Filter by status
  --state TEXT        Filter by state (2-letter code)
  --source TEXT       Filter by discovery source
  --limit INT         Max results (default: 50)
```

### `lgs store show`

Display full details for a store including online presences.

```
lgs store show STORE_ID
```

### `lgs store edit`

Update a store's fields.

```
lgs store edit STORE_ID [OPTIONS]

Options:
  --name TEXT         New name
  --status TEXT       New status
  --phone TEXT        New phone
  --notes TEXT        New notes
```

## Online Presence

### `lgs presence add`

Link a new online presence to a store.

```
lgs presence add STORE_ID --url URL --channel TYPE [OPTIONS]

Options:
  --platform TEXT     E-commerce platform
  --sells-singles     Whether it sells MTG singles
```

### `lgs presence list`

Show all presences for a store.

```
lgs presence list STORE_ID
```

### `lgs presence edit`

Update a presence's fields.

```
lgs presence edit PRESENCE_ID [OPTIONS]

Options:
  --url TEXT           New URL
  --platform TEXT      New platform
  --sells-singles      Set sells_mtg_singles
  --status TEXT        New status
```

### `lgs presence remove`

Remove a presence (soft-delete by default).

```
lgs presence remove PRESENCE_ID [OPTIONS]

Options:
  --hard              Permanently delete instead of soft-delete
```

## Validation

### `lgs validate presence`

Check web presence for store URLs. Validates accessibility and detects soft 404s (parked domains, expired domains).

```
lgs validate presence [OPTIONS]

Options:
  --store-id UUID     Validate a specific store
  --status TEXT       Filter stores by status (default: candidate)
  --limit INT         Max stores to validate (default: 100)
  --verbose           Enable verbose logging
```

### `lgs validate platform`

Detect e-commerce platform for store websites. Identifies Crystal Commerce, BinderPOS, Shopify, WooCommerce, SquareSpace, WordPress+Stripe, and others via HTML/header signatures.

```
lgs validate platform [OPTIONS]

Options:
  --store-id UUID     Detect platform for a specific store
  --limit INT         Max presences to check (default: 100)
  --verbose           Enable verbose logging
```

### `lgs validate singles`

Detect MTG singles availability on store websites. Uses three-tier detection: keyword scan, product page sampling, and LLM fallback (budget-capped). Requires `ANTHROPIC_API_KEY` for LLM tier.

```
lgs validate singles [OPTIONS]

Options:
  --store-id UUID     Detect singles for a specific store
  --limit INT         Max presences to check (default: 100)
  --verbose           Enable verbose logging
```

### `lgs validate run`

Run the full validation pipeline: presence check, platform detection, then singles detection. Processes stores sequentially with per-store error isolation.

```
lgs validate run [OPTIONS]

Options:
  --status TEXT       Filter stores by status (default: candidate)
  --limit INT         Max stores to validate (default: 100)
  --dry-run           Show what would be done without changes
  --verbose           Enable verbose logging
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string (pooler URL, `+psycopg` driver) |
| `MIGRATION_DATABASE_URL` | No | Direct connection for Alembic migrations |
| `TEST_DATABASE_URL` | No | Separate test database |
| `GOOGLE_PLACES_API_KEY` | For `discover google` | Google Places API key |
| `ANTHROPIC_API_KEY` | For LLM singles detection | Anthropic API key |
| `LLM_BUDGET_CENTS` | No | Max LLM spend per validation run (default: 500) |
