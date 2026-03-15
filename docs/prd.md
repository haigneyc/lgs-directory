# Product Requirements Document

## LGS Directory
**US Local Game Store Online Presence Database**

Version 1.0 | March 2026 | Draft

Author: Chris

---

## 1. Overview

The LGS Directory is a comprehensive, structured database of every local game store (LGS) in the United States that participates in the Magic: The Gathering ecosystem. The directory catalogs both brick-and-mortar and online presences, creating a foundational data asset that enables multiple downstream applications including price arbitrage detection, consumer discovery tools, and market intelligence products.

This PRD covers the MVP scope: building and maintaining the directory itself. Downstream features such as price scraping, arbitrage alerting, and public-facing web interfaces are explicitly out of scope for this phase but are referenced as future opportunities to inform architectural decisions.

## 2. Problem Statement

There is no centralized, structured, and actively maintained database of US local game stores with validated online presence data. The Wizards Play Network (WPN) store locator provides basic location data but does not track whether stores sell online, what e-commerce platform they use, or how actively they maintain their online inventory. This gap creates several problems:

- **For consumers:** Finding LGS online storefronts requires manual Google searches per store, and there is no way to discover which stores sell MTG singles online.
- **For sellers/arbitrageurs:** Identifying stores with stale or underpriced inventory requires manually checking hundreds of independent websites.
- **For market intelligence:** There is no aggregate view of the LGS e-commerce landscape, platform distribution, or inventory coverage.

## 3. Goals and Success Criteria

### 3.1 Primary Goals

1. **Discover:** Identify all US-based local game stores that are part of the Magic: The Gathering ecosystem.
2. **Validate:** Determine which stores have an online presence and whether they sell MTG singles online.
3. **Enrich:** Capture structured metadata about each store including e-commerce platform, inventory scope, and pricing freshness indicators.
4. **Maintain:** Keep the directory current by detecting new stores, closures, and changes to online presences.

### 3.2 Success Criteria (MVP)

| Metric | Target |
|--------|--------|
| Total US stores cataloged | > 3,000 (estimated WPN store count) |
| Online presence validation rate | > 90% of stores checked for web presence |
| E-commerce platform detection accuracy | > 85% for known platforms (Crystal Commerce, BinderPOS, Shopify, etc.) |
| Data freshness | Full re-validation cycle completes within 30 days |
| False positive rate (store marked as selling singles but does not) | < 10% |

## 4. Data Model

The data model separates the physical store entity from its online presences, reflecting the reality that a single LGS may operate across multiple online channels.

### 4.1 Store Entity

Represents a single physical local game store.

| Field | Type | Description |
|-------|------|-------------|
| store_id | UUID | Primary key |
| name | String | Store name |
| address | Object | Street, city, state, zip |
| lat/lng | Float | Geocoded coordinates |
| phone | String | Primary phone number |
| wpn_id | String (nullable) | Wizards Play Network identifier if WPN-authorized |
| wpn_level | Enum (nullable) | WPN level (Core, Premium, etc.) |
| google_place_id | String (nullable) | Google Places identifier for deduplication |
| status | Enum | candidate \| verified \| active \| unresponsive \| closed |
| discovery_source | Enum | wpn \| google_places \| tcgplayer \| manual |
| first_seen | Timestamp | When this store was first discovered |
| last_validated | Timestamp | When the store record was last validated |
| notes | Text | Free-form notes for manual annotations |

### 4.2 Online Presence

Represents a single online channel for a store. One store can have many online presences.

| Field | Type | Description |
|-------|------|-------------|
| presence_id | UUID | Primary key |
| store_id | UUID (FK) | Link to parent store entity |
| channel_type | Enum | website \| tcgplayer \| ebay \| facebook \| other |
| url | String | URL of the online presence |
| platform | Enum (nullable) | crystal_commerce \| binderpos \| shopify \| squarespace \| woocommerce \| wordpress_stripe \| custom \| unknown |
| sells_mtg_singles | Boolean (nullable) | Whether MTG singles are available for purchase |
| estimated_inventory_size | Enum (nullable) | none \| small (<500) \| medium (500-5000) \| large (>5000) |
| pricing_method | Enum (nullable) | manual \| synced \| unknown |
| last_price_update_detected | Timestamp (nullable) | Most recent detected change in pricing data |
| http_status | Integer (nullable) | Last HTTP response code |
| last_checked | Timestamp | Last time this presence was crawled/checked |
| status | Enum | active \| unreachable \| dead |

### 4.3 Validation Log

Audit trail for every automated or manual check performed on a store or online presence.

| Field | Type | Description |
|-------|------|-------------|
| log_id | UUID | Primary key |
| store_id | UUID (FK) | Store being validated |
| presence_id | UUID (FK, nullable) | Online presence being validated (null for store-level checks) |
| check_type | Enum | http_check \| platform_detect \| singles_detect \| closure_detect \| manual_review |
| result | JSON | Structured result of the check |
| timestamp | Timestamp | When the check was performed |

## 5. Discovery Pipeline

Discovery is the process of finding candidate stores and ingesting them into the directory. The pipeline runs from multiple sources, deduplicates results, and feeds the validation pipeline.

### 5.1 Discovery Sources

| Source | Method | Expected Yield | Strengths | Weaknesses |
|--------|--------|---------------|-----------|------------|
| WPN Store Locator | Web scrape of locator.wizards.com | ~3,000+ stores | Most complete list of authorized MTG retailers | No online presence data; includes stores with no web presence |
| Google Places API | Search by category + region | ~2,000-4,000 results | Includes website URLs; rich metadata | Noisy; includes non-MTG game stores, cafes, etc. |
| TCGPlayer Seller Directory | Scrape seller listings | ~1,000-2,000 sellers | Confirms online selling capability | Many are individuals, not LGS; some lack independent sites |
| Facebook | Search Marketplace listings + Shop/business pages for LGS storefronts | ~500-1,500 stores | Catches stores that sell primarily via social channels; many LGS maintain active Facebook shops | Requires Facebook Graph API or scraping; noisy results; rate limits |
| Manual / Community | User submissions, Reddit | Ongoing trickle | Catches edge cases automated sources miss | Unstructured; requires validation |

### 5.2 Deduplication Strategy

Stores discovered from multiple sources must be deduplicated into a single store entity. The deduplication pipeline uses a tiered matching approach:

0. **External ID match:** Exact match on `google_place_id` (confidence 1.0).
1. **WPN ID match:** Exact match on `wpn_id` (confidence 1.0).
2. **Name + ZIP match:** Identical normalized name + zip code (confidence 0.95).
3. **Address match:** Same normalized street + city + state after abbreviation expansion and suite stripping (confidence 0.90).
4. **Fuzzy match:** Levenshtein distance on name (>85%) + geographic proximity (<0.5 miles) or same ZIP. Flagged for manual review if confidence is below 0.92.

When merging, the system preserves all source IDs (WPN ID, Google Place ID, TCGPlayer seller ID) on the unified store entity to maintain linkage back to discovery sources.

## 6. Validation Pipeline

Validation enriches candidate stores with structured metadata about their online presences. This is the core value-add of the directory and the most engineering-intensive component.

### 6.1 Stage 1: Web Presence Detection

For each candidate store, determine whether it has an online presence.

- **Input:** Store name, address, phone, any known URLs from discovery sources.
- **Process:** If no URL is known, perform a targeted Google search (store name + city + state + "MTG" or "Magic the Gathering"). Check the top 3-5 results for relevance. Validate any known URLs with an HTTP HEAD request.
- **Output:** Zero or more online_presence records linked to the store, each with a URL and channel_type.

### 6.2 Stage 2: Platform Detection

For each confirmed website, identify the e-commerce platform.

Platform fingerprinting relies on detectable signatures in HTML, headers, cookies, and URL patterns. Key signatures include:

| Platform | Detection Signals |
|----------|------------------|
| Crystal Commerce | "Powered by Crystal Commerce" footer, /products/ URL pattern, specific CSS class names (cc-product-list), crystalcommerce.com asset references |
| BinderPOS | binderpos.com API calls, specific JavaScript bundle references, /shop/ URL structure |
| Shopify | Shopify CDN references (cdn.shopify.com), /collections/ URL pattern, X-ShopId header |
| WooCommerce | wc-add-to-cart CSS classes, /wp-content/ paths, woocommerce-specific meta tags |
| SquareSpace | squarespace.com CDN, specific JSON config patterns |
| WordPress + Stripe | /wp-content/ paths, WordPress meta generator tag, Stripe.js script references (js.stripe.com), stripe-button CSS classes |
| Custom / Bespoke | No known platform fingerprint detected, but cart/checkout patterns present (add-to-cart buttons, cart icons, checkout flows), Stripe.js or PayPal SDK references, AND product page heuristics (card names, set names, rarity/condition fields, price elements) |
| TCGPlayer Direct | store.tcgplayer.com subdomain or integration scripts |

### 6.3 Stage 3: MTG Singles Detection

Determine whether the online presence includes MTG singles for sale. This is the most nuanced validation step.

- **Keyword scanning:** Search site content and navigation for terms like "Magic: The Gathering," "MTG Singles," "Magic Singles," category/collection pages with MTG references.
- **Product page sampling:** If a product catalog is detected, sample 5-10 product pages to check for MTG card attributes (set name, card name, rarity, condition).
- **LLM classification (fallback):** For ambiguous cases, send a page snapshot to the Claude API for classification. Keep this as a fallback to control costs.

Output updates the sells_mtg_singles and estimated_inventory_size fields on the online presence record.

### 6.4 Stage 4: Freshness and Pricing Signals

For stores confirmed to sell MTG singles online, capture signals about pricing freshness. This stage is lightweight in the MVP but is the critical bridge to future arbitrage features.

- **Last modified detection:** Check HTTP Last-Modified headers, sitemap lastmod dates, and any visible "last updated" timestamps on product pages.
- **Price snapshot:** For a small sample of high-liquidity cards (e.g., 10 staple cards across formats), record the listed price and timestamp. On subsequent checks, detect whether prices have changed.
- **Pricing method inference:** If prices match a known market feed (TCGPlayer Market Price, Card Kingdom pricing) within a tight tolerance, mark as "synced." If prices diverge significantly or show no change over multiple check cycles, mark as "manual."

## 7. Lifecycle Management

The directory must stay current. Stores open and close constantly, websites go up and down, and e-commerce presences change platforms. Lifecycle management handles all of this.

### 7.1 Store Status Transitions

| From | To | Trigger |
|------|----|---------|
| candidate | verified | At least one validation check completed successfully |
| verified | active | Online presence confirmed with sells_mtg_singles = true |
| active | unresponsive | 3 consecutive failed HTTP checks across all online presences |
| unresponsive | active | Successful HTTP check + content validation |
| unresponsive | closed | Google listing marked permanently closed, OR domain expired, OR WPN delisting confirmed |
| any | closed | Manual review confirms permanent closure |

### 7.2 Scheduled Tasks

| Task | Frequency | Description |
|------|-----------|-------------|
| HTTP health check | Weekly | HEAD request to all known URLs; update http_status and flag unreachable presences |
| Full validation cycle | Monthly | Re-run platform detection and singles detection on all active presences |
| Discovery re-crawl | Monthly | Re-run all discovery sources and diff against existing stores to find new entries |
| Freshness check | Bi-weekly | Re-check price sample for stores with sells_mtg_singles = true |
| Closure detection | Monthly | Cross-reference Google Places status, WPN locator, and domain registrar data |

### 7.3 Alerting

The system should surface notable changes for manual review:

- **New store discovered:** Any store found in a re-crawl that doesn't match an existing entity.
- **Store went offline:** An active store whose website has been unreachable for 2+ consecutive checks.
- **Platform change detected:** Store appears to have migrated e-commerce platforms.
- **Significant price divergence:** A store's sample prices diverge from market by more than 30% (potential arbitrage signal or data error).

## 8. Technical Architecture

### 8.1 Stack Recommendations

Given the solo-developer context, the architecture prioritizes simplicity, low operational overhead, and the ability to run locally or on a single server.

- **Language:** Python 3.11+ (rich ecosystem for scraping, HTTP, and data processing).
- **Database:** Supabase (managed PostgreSQL with built-in auth, REST API, and realtime subscriptions). Supports JSONB fields for flexible validation results, robust full-text search for deduplication.
- **ORM:** SQLAlchemy 2.0+ with Alembic migrations.
- **HTTP:** httpx for API/scraping requests; Playwright for Akamai cookie harvesting.
- **Parsing:** BeautifulSoup4 for HTML parsing in platform/singles detection.
- **CLI:** Click + Rich for command-line interface.
- **Task scheduling:** Simple cron jobs for MVP; migrate to Celery or APScheduler if complexity warrants.
- **LLM integration:** Claude API via Anthropic SDK for ambiguous classification tasks (budget-capped per run).
- **Storage:** Supabase Storage for page snapshots and screenshots; S3-compatible bucket for long-term archival if needed.

### 8.2 Repository Structure

Single repository with clear module separation:

```
src/lgs_directory/
  models/          Store, OnlinePresence, ValidationLog, enums
  discovery/       WPN scraper, Google Places scraper, browser cookies,
                   normalization, deduplication, ingestion
  validation/      Web presence, platform detection, singles detection,
                   orchestrator
  cli/             Click commands: discover, store, presence, validate
  config.py        Pydantic settings
  db.py            Engine/session management
  schemas.py       Pydantic address validation
tests/             Unit and integration tests
```

See `docs/cli_reference.md` for full CLI documentation.

### 8.3 Cost Controls

Several pipeline stages incur costs that need to be managed:

- **Oxylabs:** Budget proxy usage by prioritizing direct requests first and only routing through Oxylabs when direct requests are blocked or rate-limited.
- **Google Places API:** Cache results aggressively (place details change slowly). Use the Nearby Search endpoint with category filters to minimize per-query costs.
- **Claude API:** Reserve LLM classification for genuinely ambiguous cases. Set a per-run budget cap (e.g., max 100 API calls per validation cycle). Log every call with cost.
- **Overall:** Target total monthly operating cost under $100 for the MVP phase.

## 9. Future Opportunities (Out of Scope)

These are explicitly not part of the MVP but should inform architectural decisions:

- **Price arbitrage engine:** Automated scraping of product catalogs from validated stores with online singles, cross-referenced against market prices to identify arbitrage opportunities.
- **Public directory website:** Consumer-facing site for discovering LGS online storefronts, filterable by location, platform, inventory size, etc. Monetizable via affiliate links, featured listings, or premium access.
- **API product:** Structured API access to the directory data for third-party tools, price aggregators, or market research firms.
- **International expansion:** Extending the directory to Canada, EU (via CardMarket integration), Japan, and other markets.
- **Inventory intelligence:** Tracking inventory levels and turnover rates across stores to identify supply/demand imbalances.

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| WPN Store Locator changes or blocks scraping | High - primary discovery source lost | Cache full locator data on first successful crawl; build fallback to Google Places as primary source; monitor for changes |
| Crystal Commerce or other platforms block automated access | Medium - validation pipeline degraded | Use Oxylabs proxies; implement respectful rate limiting; fingerprint from cached/snapshot data rather than live requests |
| LGS closure rate higher than expected | Low - directory accuracy degrades | Increase closure detection frequency; add community-sourced reporting as a signal |
| Deduplication produces false merges | Medium - data quality issues | Conservative matching thresholds; manual review queue for low-confidence merges; easy split/unmerge in CLI |
| Cost overruns on API/proxy usage | Low - budget exceeded | Hard budget caps per pipeline run; cost logging and alerting; graceful degradation (skip expensive steps when budget exhausted) |

## 11. MVP Implementation Phases

### Phase 0: Foundation (Week 1-2) ✅ COMPLETE

Set up repository structure, database schema, and basic CLI. Implement the store and online_presence models. Create manual add/edit/list commands.

**Delivered:** Project skeleton, SQLAlchemy models (Store, OnlinePresence, ValidationLog), CLI CRUD commands (`lgs store add/list/show/edit`, `lgs presence add/list/edit/remove`), Alembic migrations, Supabase PostgreSQL integration, Pydantic address validation, full test suite.

### Phase 1: Discovery (Week 2-4) ✅ COMPLETE

Implement WPN Store Locator scraper as the primary source. Build deduplication pipeline. Run initial ingestion to establish baseline store count. ~~Add Google Places API integration as secondary source.~~

**Delivered:** WPN GraphQL API scraper (`discovery/wpn.py`), address normalization (`discovery/normalize.py`), 4-tier deduplication pipeline (`discovery/dedup.py` — WPN ID, name+ZIP, address, fuzzy+proximity), ingestion orchestrator (`discovery/ingest.py`), CLI commands (`lgs discover wpn`, `lgs discover status`), `--source` filter on `lgs store list`, JSON cache save/load for replay. 54 tests passing, ruff/mypy clean.

### Phase 1.5: Discovery Hardening ✅ COMPLETE

Akamai bot protection bypass and Google Places API integration.

**Delivered:** Playwright cookie harvesting (`discovery/browser.py`), `WpnScraper` cookie passthrough, Google Places Text Search API grid scanner (`discovery/google_places.py`), Google Places ingestion pipeline (`discovery/ingest_google.py`), `google_place_id` column + index on Store model, dedup tier 0.5 for google_place_id matching, CLI `lgs discover google` command. 3 new dependencies: playwright, beautifulsoup4, anthropic.

### Phase 2: Validation ✅ COMPLETE

Web presence detection, platform fingerprinting, MTG singles detection, and full validation orchestrator.

**Delivered:** Web presence validator with soft 404 detection (`validation/web_presence.py`), HTML/header-based platform fingerprinting for 7 platforms (`validation/platform_detect.py`), 3-tier MTG singles detection — keyword scan, product page sampling, LLM fallback (`validation/singles_detect.py`), validation orchestrator with per-store error isolation and LLM budget tracking (`validation/orchestrator.py`), CLI commands (`lgs validate presence/platform/singles/run`), OnlinePresence seeding from WPN and Google Places website URLs during ingestion. 117 tests passing, ruff clean.

### Phase 3: Lifecycle (Week 7-9)

Implement scheduled health checks and validation cycles. Build re-discovery diff logic. Add alerting for notable changes. Implement status transition logic.

### Phase 4: Freshness (Week 9-10)

Implement price sampling for validated stores. Build pricing method inference. Establish baseline freshness data for arbitrage readiness assessment.
