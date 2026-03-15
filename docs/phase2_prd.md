# Phase 2 PRD — Validation + Discovery Hardening

**LGS Directory** | March 2026

**Status: ✅ FULLY IMPLEMENTED** (March 2026)

---

## Phase 1.5: Discovery Hardening ✅

Both items implemented.

### 1. Akamai Bot Protection Bypass ✅

The WPN GraphQL API (`api.tabletop.wizards.com/silverbeak-griffin-service/graphql`) is behind Akamai Bot Manager. Plain httpx requests get `400 Bad Request` because Akamai requires JavaScript-generated sensor data cookies (`ak_bmsc`, `bm_sv`).

#### Option A: Playwright Cookie Harvesting (Recommended)

**Approach:** Use Playwright to load `locator.wizards.com` once per scrape session, extract Akamai cookies, then pass them to httpx for the actual GraphQL pagination.

**Why this wins:**
- Free — no ongoing proxy costs
- Fast — single browser launch (~3s), then 11 paginated httpx requests
- Cookies last ~30 minutes, more than enough for a full scrape
- Playwright is already available in the dev environment

**Implementation:**
```
discovery/
  browser.py    # Playwright cookie harvesting
```

- `get_akamai_cookies() -> dict[str, str]` — launches headless Chromium, navigates to `locator.wizards.com`, waits for Akamai challenge to resolve, extracts cookies, closes browser
- `WpnScraper` gets a `cookies` parameter — if provided, attaches to all httpx requests
- CLI: `lgs discover wpn` calls `get_akamai_cookies()` before scraping

**New dependency:** `playwright` (plus `playwright install chromium` post-install step)

#### Option B: Oxylabs Web Unblocker

**Approach:** Proxy GraphQL requests through Oxylabs' Web Unblocker product, which handles Akamai JS challenges server-side.

**Why consider it:**
- Zero browser dependency — simpler CI/CD
- Handles fingerprinting evolution automatically (Oxylabs maintains bypass)
- Already referenced in the PRD tech stack (Section 8.1)

**Tradeoffs:**
- Cost: ~$3/1k requests (premium tier). Our 11-request scrape is cheap, but adds up with re-crawls
- External dependency on Oxylabs uptime
- Requires API key management

**Implementation:**
- Add `OXYLABS_USERNAME` and `OXYLABS_PASSWORD` to config
- Route httpx requests through `http://unblock.oxylabs.io` proxy
- Fallback to direct requests if proxy is unavailable

#### Decision

**Implemented Option A (Playwright).** `discovery/browser.py` launches headless Chromium, navigates to `locator.wizards.com`, waits for challenge resolution, extracts `ak_bmsc`/`bm_sv` cookies. CLI `lgs discover wpn` auto-harvests before scraping with graceful fallback if Playwright isn't installed.

### 2. Google Places API Integration ✅

Adds a secondary discovery source for stores not in the WPN network.

**Endpoint:** Google Places Nearby Search → Place Details

**Implementation:**
```
discovery/
  google_places.py    # Google Places API client
```

- `GooglePlacesScraper` class
- Grid-scan US with category filter (`game_store`, `hobby_shop`)
- Extract: name, address, phone, website URL, place_id, rating
- Rate limit: 100 req/sec (generous API limits with billing enabled)
- Dedup against existing stores using the same pipeline

**New dependency:** None (httpx suffices for REST API calls)
**Requires:** `GOOGLE_PLACES_API_KEY` in config

**Store model change:** Added `google_place_id: String(100)` field with index `ix_stores_google_place_id`. Migration: `alembic/versions/e2450fae7f86_add_google_place_id.py`.

**Implementation notes:** Uses Google Places Text Search (New) API. Grid-scans contiguous US with 1-degree cells, 50km radius, 4 search categories. Deduplicates by `place_id` within results. Ingestion pipeline (`discovery/ingest_google.py`) reuses `IngestReport` from WPN ingestion. Seeds `OnlinePresence` from Google `websiteUri` during ingestion. Dedup extended with tier 0.5: exact `google_place_id` match (confidence 1.0).

---

## Phase 2: Validation Pipeline ✅

The core value-add. For every discovered store, determine whether it has an online presence and what it sells.

### Step 1: Web Presence Detection ✅

For each store without a known URL, find its website.

**Sources (checked in order):**
1. WPN scraper already provides `website` field for many stores — use it
2. Google Places `website` field (from Phase 1.5)
3. Google Search fallback: `"{store name}" "{city}, {state}" MTG singles` — parse top 3 results

**Implementation:**
```
validation/
  __init__.py
  web_presence.py     # URL discovery + HTTP health check
```

- `detect_web_presence(store: Store) -> list[OnlinePresence]`
- HTTP HEAD/GET to validate URLs (follow redirects, check for soft 404s)
- Create OnlinePresence records with `channel_type=website`, `status=active|unreachable|dead`
- Log results to ValidationLog (`check_type=http_check`)

**CLI:** `lgs validate presence [--store-id UUID] [--status candidate] [--limit 100]`

**Implementation notes:** Checks existing `OnlinePresence` records (seeded during WPN/Google ingestion). HTTP GET with redirect following (max 5). Soft 404 detection via regex patterns for parked domains, expired domains, "page not found", sedoparking, hugedomains, etc. Creates `ValidationLog` entries with `check_type=HTTP_CHECK`.

### Step 2: Platform Detection ✅

Fingerprint the e-commerce platform for each confirmed website.

**Detection signals** (from PRD Section 6.2):
| Platform | Primary Signal |
|----------|---------------|
| Crystal Commerce | `crystalcommerce.com` asset refs, `cc-product-list` CSS class |
| BinderPOS | `binderpos.com` API calls, `/shop/` URL structure |
| Shopify | `cdn.shopify.com` refs, `X-ShopId` header |
| WooCommerce | `wc-add-to-cart` CSS, `/wp-content/` paths |
| SquareSpace | `squarespace.com` CDN |
| WordPress + Stripe | `/wp-content/` + `js.stripe.com` script |
| TCGPlayer Direct | `store.tcgplayer.com` subdomain |

**Implementation:**
```
validation/
  platform_detect.py  # Platform fingerprinting engine
```

- `detect_platform(url: str) -> Platform` — fetches page, runs signature checks
- Returns `Platform` enum value (already defined in models)
- Respects rate limits, uses httpx with sensible timeouts
- Logs to ValidationLog (`check_type=platform_detect`)

**CLI:** `lgs validate platform [--store-id UUID] [--limit 100]`

**Implementation notes:** Ordered signature list — first match wins. Checks HTML patterns, HTTP headers (`x-shopid`, `x-shopify-stage`), and URL patterns. Crystal Commerce checked before Shopify to handle overlap. WordPress+Stripe requires both `wp-content` and `js.stripe.com` present. TCGPlayer Direct matched on URL, not HTML. Returns `Platform.UNKNOWN` when no signatures match.

### Step 3: MTG Singles Detection ✅

Determine whether a website sells Magic: The Gathering singles.

**Approach:**
1. **Keyword scan:** Check page text + navigation for "Magic: The Gathering", "MTG Singles", "Magic Singles", "Single Cards"
2. **Product page sampling:** If catalog detected, sample 5-10 product pages for card attributes (set name, card name, rarity, condition, NM/LP/MP)
3. **LLM fallback:** For ambiguous cases, send page snapshot to Claude API for classification (budget-capped)

**Implementation:**
```
validation/
  singles_detect.py   # MTG singles detection
```

- `detect_singles(url: str, platform: Platform) -> SinglesResult`
- Returns: `sells_mtg_singles: bool`, `estimated_inventory_size: InventorySize`, `confidence: float`
- Logs to ValidationLog (`check_type=singles_detect`)

**CLI:** `lgs validate singles [--store-id UUID] [--limit 100]`

**Implementation notes:** Three-tier detection: (1) keyword scan for MTG terms — 2+ hits = 0.85 confidence, 1 hit = 0.60; (2) product page sampling via BeautifulSoup link extraction — checks for card conditions (NM/LP/MP), rarity terms, MTG set names; (3) LLM fallback using Claude Haiku with budget cap (configurable via `LLM_BUDGET_CENTS`, default 500). High-confidence keyword match (>=0.80) short-circuits further tiers.

### Step 4: Full Validation Orchestrator ✅

Runs all three stages in sequence for a batch of stores.

**Implementation:**
```
validation/
  orchestrator.py     # Runs presence → platform → singles
```

- `validate_stores(session, *, status_filter, limit, dry_run) -> ValidationReport`
- Progress tracking + Rich output
- Respects per-run budget cap for LLM calls

**CLI:** `lgs validate run [--status candidate] [--limit 100] [--dry-run]`

**Implementation notes:** Runs presence → platform → singles sequentially per store. Per-store error isolation (one failure doesn't stop the batch). LLM budget tracked across the entire run (~5 cents per Haiku call). Reports: `ValidationReport` dataclass with total_stores, presences_found, platforms_detected, singles_detected, llm_calls, llm_spend_cents, errors.

---

## New Dependencies (Phase 2) ✅ Installed

| Package | Purpose |
|---------|---------|
| `playwright` | Akamai cookie harvesting (Phase 1.5) |
| `beautifulsoup4` | HTML parsing for platform detection + singles detection |
| `anthropic` | Claude API for LLM classification fallback |

## New Config Keys ✅ Added

| Key | Required | Description |
|-----|----------|-------------|
| `GOOGLE_PLACES_API_KEY` | For `discover google` | Google Places API |
| `ANTHROPIC_API_KEY` | For LLM singles detection | Claude API for ambiguous classification |
| `LLM_BUDGET_CENTS` | No (default 500) | Max LLM spend per validation run in cents |

Oxylabs keys were not implemented (Playwright approach chosen instead).

## Migration ✅ Done

- `alembic/versions/e2450fae7f86_add_google_place_id.py` — adds `google_place_id` column + index

## Verification Criteria

1. ✅ `lgs discover wpn` harvests Akamai cookies via Playwright before scraping
2. ✅ `lgs discover google [--dry-run]` fetches Google Places stores
3. ✅ `lgs validate presence --status candidate --limit 10` checks URLs
4. ✅ `lgs validate platform --limit 10` identifies platforms via HTML signatures
5. ✅ `lgs validate singles --limit 10` detects MTG singles (keyword/product/LLM)
6. ✅ `lgs validate run --status candidate --limit 50` runs full pipeline
7. ✅ 117 tests passing (all non-DB tests)
8. ✅ `ruff check` clean

## Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_config.py` | 4 | Config keys, defaults, overrides |
| `test_browser.py` | 5 | Cookie extraction, WpnScraper passthrough |
| `test_google_places.py` | 12 | Address parsing, place parsing, scraper, dedup |
| `test_web_presence.py` | 10 | Soft 404, URL checking, timeout handling |
| `test_platform_detect.py` | 10 | All 7 platform signatures + unknown + priority |
| `test_singles_detect.py` | 12 | Keyword scan, product links, full pipeline, LLM |
| `test_orchestrator.py` | 5 | Report, dry-run, error isolation, budget |
| `test_cli_validate.py` | 5 | CLI help, presence, run dry-run |
| *(existing tests)* | 54 | Models, WPN, normalize, dedup, CLI store/presence |
