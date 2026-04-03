# Programmatic SEO Pages — Design Spec

**Date:** 2026-04-02
**Author:** Kira (Architect) + Chris
**Project:** lgs-directory
**Status:** Approved

---

## Overview

Generate state and city pages programmatically from the existing 5,500-store dataset to capture long-tail search traffic ("game stores in Austin TX", "MTG stores in Texas"). Revenue comes from affiliate links on "buy cards online" sections and eventually premium store listings.

**Goal:** $200-300/mo passive revenue within 10-12 months via SEO traffic → affiliate clicks.

---

## Phase 1 — Programmatic SEO Pages (Existing Data)

### Route Structure

```
/stores/[state]/            → State page     (e.g., /stores/texas)
/stores/[state]/[city]/     → City page      (e.g., /stores/texas/austin)
/stores/[id]                → Store detail   (existing, unchanged)
/sitemap.xml                → Dynamic sitemap
/robots.txt                 → Standard crawl rules
/llms.txt                   → LLM-readable site description
```

**Slug format:**
- States: lowercase, hyphenated — `new-york`, `texas`, `north-carolina`
- Cities: lowercase, hyphenated — `austin`, `new-york-city`, `san-francisco`
- Slugs derived from `address->>'state'` and `address->>'city'` at query time

**Indexing rules:**
- City pages only generated for cities with **2+ active/verified stores**
- Closed and unresponsive stores excluded from SEO pages
- Store statuses shown: `active`, `verified`, `candidate`

### State Page (`/stores/[state]/`)

**Layout (top to bottom):**

1. **Breadcrumb** — Home → Texas (rendered + JSON-LD `BreadcrumbList`)
2. **Title** — "Game Stores in Texas"
3. **Stats bar** — "247 stores · 180 active · 12 WPN Premium · 45 sell online"
4. **Map** — Leaflet map with all stores in the state pinned (reuse `StoreMap` component)
5. **City grid** — All cities with 2+ stores, linked, with store counts. Grouped alphabetically. Example: "Austin (12) · Dallas (18) · Houston (24)"
6. **Store table** — Full paginated store listing for the state (reuse `StoreTable` + `Pagination`)

**SEO metadata:**
- `title`: "Game Stores in Texas | LGS Directory"
- `description`: "Find {count} local game stores in Texas. Browse MTG shops, WPN stores, and online card sellers."
- `og:title`, `og:description`, `og:type: website`
- JSON-LD: `ItemList` of `LocalBusiness` entities + `BreadcrumbList`

### City Page (`/stores/[state]/[city]/`)

**Layout (table-first, top to bottom):**

1. **Breadcrumb** — Home → Texas → Austin (rendered + JSON-LD)
2. **Title** — "Game Stores in Austin, TX"
3. **Stats bar** — "12 stores · 8 active · 3 WPN Premium · 5 sell online"
4. **AI description** (Phase 2 — placeholder text or omitted in Phase 1)
5. **Store table** — All stores in this city, paginated
6. **Two-column section:**
   - Left: Leaflet map with city stores pinned
   - Right: "Buy Cards Online" — stores with `sells_mtg_singles = true`, showing platform, inventory size, and link (affiliate-tagged)
7. **Nearby cities** — Other cities in the same state with store counts, linked. Ordered by store count descending. Max 8 cities.

**SEO metadata:**
- `title`: "Game Stores in Austin, TX | LGS Directory"
- `description`: "Find {count} local game stores in Austin, Texas. Browse MTG shops, check online card sellers, and find WPN-authorized stores."
- JSON-LD: `ItemList` of `LocalBusiness` + `BreadcrumbList`
- Each store in JSON-LD includes: name, address, telephone, geo coordinates, url (if available)

### "Buy Cards Online" Section

This section surfaces stores with active online presences where `sells_mtg_singles = true`.

**Per store row:**
- Store name (links to store detail page)
- External shop link (affiliate-tagged, opens in new tab)
- Platform badge (Crystal Commerce, Shopify, BinderPOS, etc.)
- Inventory size indicator (Small / Medium / Large)

**Affiliate integration:**
- TCGPlayer affiliate links: apply to TCGPlayer affiliate program, tag outbound URLs with affiliate ID
- eBay Partner Network: tag eBay outbound URLs
- Direct store links: no affiliate tag (but still valuable for user experience)

### Schema.org JSON-LD

Every page includes structured data:

**State and city pages:**
```json
{
  "@context": "https://schema.org",
  "@type": "ItemList",
  "name": "Game Stores in Austin, TX",
  "numberOfItems": 12,
  "itemListElement": [
    {
      "@type": "LocalBusiness",
      "name": "Pat's Games",
      "address": {
        "@type": "PostalAddress",
        "streetAddress": "...",
        "addressLocality": "Austin",
        "addressRegion": "TX",
        "postalCode": "78701"
      },
      "geo": {
        "@type": "GeoCoordinates",
        "latitude": 30.2672,
        "longitude": -97.7431
      },
      "telephone": "+1-512-555-0100",
      "url": "https://patsgames.com"
    }
  ]
}
```

**Breadcrumbs (every page):**
```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://lgs-directory.com/" },
    { "@type": "ListItem", "position": 2, "name": "Texas", "item": "https://lgs-directory.com/stores/texas" },
    { "@type": "ListItem", "position": 3, "name": "Austin", "item": "https://lgs-directory.com/stores/texas/austin" }
  ]
}
```

### /llms.txt

```
# LGS Directory
> A comprehensive directory of local game stores in the United States.

## What this site contains
- 5,500+ local game stores across all 50 US states
- Store details: name, address, phone, WPN authorization status
- Online presence: website URLs, e-commerce platforms, MTG singles availability
- Location data: latitude/longitude coordinates for mapping

## How to use this data
- Browse by state: /stores/{state-name}
- Browse by city: /stores/{state-name}/{city-name}
- Individual store: /stores/{store-uuid}
- Sitemap: /sitemap.xml

## Data freshness
- Store data validated every 12 hours via automated pipeline
- Sources: WPN Store Locator, Google Places API
```

### Dynamic Sitemap (`/sitemap.xml`)

Generated via Next.js `sitemap.ts` in the app directory.

**Includes:**
- Homepage `/`
- All state pages `/stores/[state]/`
- All city pages with 2+ active/verified stores `/stores/[state]/[city]/`
- All individual store detail pages `/stores/[id]`
- `lastmod` set to `last_validated` timestamp for stores, or generation time for index pages
- `changefreq: weekly` for state/city pages, `monthly` for store details
- `priority: 0.8` for state pages, `0.6` for city pages, `0.4` for store details

**Implementation:** Single `app/sitemap.ts` that queries the DB for all valid slugs.

### robots.txt

```
User-agent: *
Allow: /

Sitemap: https://lgs-directory.com/sitemap.xml
```

### New Database Queries

```
getStateIndex()
  → [{ state, slug, store_count, active_count, wpn_premium_count, online_count }]
  → WHERE status IN ('active', 'verified', 'candidate')
  → GROUP BY address->>'state'

getCityIndex(stateSlug)
  → [{ city, slug, store_count, active_count, wpn_premium_count, online_count }]
  → WHERE state matches AND status IN ('active', 'verified', 'candidate')
  → GROUP BY address->>'city'
  → HAVING COUNT(*) >= 2

listStoresByCity(stateSlug, citySlug, page)
  → Paginated store list for a specific city
  → Same as existing listStores() but filtered by city
  → PAGE_SIZE = 25

getOnlineStores(stateSlug, citySlug?)
  → Stores with online_presences WHERE sells_mtg_singles = true
  → JOIN online_presences ON store_id
  → Returns: store name, presence URL, platform, inventory_size

getNearbyCities(stateSlug, citySlug, limit = 8)
  → Other cities in the same state, ordered by store_count DESC
  → Excludes the current city
```

### Slug Utilities

```typescript
// State: "New York" → "new-york", "Texas" → "texas"
function stateToSlug(state: string): string

// City: "New York City" → "new-york-city", "San Francisco" → "san-francisco"
function cityToSlug(city: string): string

// Reverse: "new-york" → "New York" (for display and DB queries)
function slugToState(slug: string): string
function slugToCity(slug: string): string
```

### Internal Linking Strategy

- **Homepage** links to all 50 state pages (footer or dedicated section)
- **State pages** link to all city pages within that state
- **City pages** link to up to 8 nearby cities in the same state
- **City pages** link to individual store detail pages
- **Store detail pages** link back to their city page via breadcrumb
- **All pages** have breadcrumb navigation linking up the hierarchy

### Component Reuse

| Existing Component | Reused On |
|---|---|
| `StoreTable` | State pages, city pages |
| `Pagination` | State pages, city pages |
| `StoreStatusBadge` | State pages, city pages |
| `WpnBadge` | State pages, city pages |
| `StoreMap` (dynamic) | State pages, city pages |

**New components:**
- `Breadcrumb` — renders breadcrumb trail + JSON-LD
- `StatsBar` — "X stores · Y active · Z premium · W sell online"
- `CityGrid` — alphabetical grid of city links with store counts
- `OnlineStoresCard` — "Buy Cards Online" section with affiliate links
- `NearbyCities` — pill-style links to nearby city pages
- `JsonLd` — renders `<script type="application/ld+json">` in head

---

## Phase 2 — Data Enrichment + AI + MCP (Future)

### Data Enrichment Pipeline

- **Google Places enrichment:** Fetch hours, photos, ratings for stores with `google_place_id`. Store in a new `store_details` table or extend `stores`.
- **Website scraping:** Extract store description, products/games carried, event schedules from store websites. Use BeautifulSoup + Claude for ambiguous content.
- **AI-generated city descriptions:** Batch-generate 2-3 sentence city descriptions via Claude API. Store in a `city_metadata` table keyed by (state, city). Review queue for quality control before publishing.

### MCP Server

- Expose store queries as MCP tools: `find_stores`, `get_store`, `find_online_shops`, `nearby_stores`
- Publish to MCP registry for discoverability
- Potential rate-limited API for third-party LLM agents

### Enhanced City Pages (Phase 2)

- AI-generated city description rendered between stats bar and store table
- Store hours displayed in store table and detail pages
- Google Places photos on store detail pages
- "Games carried" tags per store (MTG, Pokemon, D&D, board games, etc.)
- Events section if event data is available

---

## Technical Notes

- **Static generation:** State and city pages can use `generateStaticParams` for build-time generation, with ISR revalidation every 24 hours (data refreshes every 12 hours via pipeline, but pages don't need to be real-time).
- **Slug collisions:** If two cities in the same state have the same slug after normalization, append a disambiguator (e.g., zip code). This is unlikely but should be handled.
- **Route disambiguation:** `/stores/[state]` vs `/stores/[id]` — state slugs are alphabetic (`texas`, `new-york`) while store IDs are UUIDs (`a2fa0716-...`). Use a regex matcher or check for UUID format to route correctly. Next.js App Router resolves this by folder structure: `/stores/[state]/` is a directory with its own `page.tsx`, while `/stores/[id]/page.tsx` already exists. Both can coexist as long as no state slug is a valid UUID (which it won't be).
- **Performance:** State pages with 200+ stores should paginate the store table. Map component should only render visible pins (Leaflet handles this natively with clustering for large sets).
- **Affiliate links:** Outbound affiliate links should use `rel="nofollow sponsored"` per Google guidelines.
- **Mobile:** Table-first layout stacks naturally on mobile. The two-column map + online shops section becomes single-column. Existing responsive patterns apply.
