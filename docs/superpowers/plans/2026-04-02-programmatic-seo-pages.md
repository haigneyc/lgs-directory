# Programmatic SEO Pages — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add auto-generated state and city pages to the LGS Directory to capture long-tail search traffic and drive affiliate revenue.

**Architecture:** Nested dynamic routes `/stores/[state]/` and `/stores/[state]/[city]/` backed by new aggregation queries against the existing PostgreSQL stores table. Reuses existing components (StoreTable, Pagination, StoreMap) and adds new ones (Breadcrumb, StatsBar, CityGrid, OnlineStoresCard, NearbyCities, JsonLd). Pages are statically generated at build time with 24-hour ISR revalidation.

**Tech Stack:** Next.js 16 (App Router), TypeScript, PostgreSQL (Neon/Supabase), Leaflet, Tailwind CSS v4, shadcn/ui

**Spec:** `docs/superpowers/specs/2026-04-02-programmatic-seo-pages-design.md`

**Project root:** `/home/chris/projects/lgs-directory`
**Web app:** `/home/chris/projects/lgs-directory/web`
**CLAUDE.md:** `/home/chris/projects/lgs-directory/web/CLAUDE.md`

**Before starting:** Read the spec, CLAUDE.md, and `web/lib/queries.ts` + `web/lib/types.ts` + `web/lib/format.ts` to understand the existing patterns. All new code must match the existing style exactly.

---

### Task 1: Slug Utilities

**Files:**
- Create: `web/lib/slugs.ts`

- [ ] **Step 1: Create slug utility functions**

```typescript
// web/lib/slugs.ts

const MAX_SLUG_LENGTH = 100;

/**
 * Maps full state names to their two-letter abbreviations.
 * Used for display (e.g., "TX" in titles) alongside full-name slugs for SEO.
 */
const STATE_ABBREVIATIONS: Record<string, string> = {
  "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
  "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
  "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
  "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
  "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
  "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
  "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
  "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
  "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
  "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
  "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
  "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
  "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
};

/** Reverse map: slug → display name */
const SLUG_TO_STATE: Record<string, string> = {};
for (const [name] of Object.entries(STATE_ABBREVIATIONS)) {
  const slug = name.replace(/\s+/g, "-");
  SLUG_TO_STATE[slug] = name
    .split(" ")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** "New York" → "new-york" */
export function stateToSlug(state: string): string {
  console.assert(typeof state === "string", "stateToSlug: state must be a string");
  console.assert(state.length > 0, "stateToSlug: state must not be empty");
  const slug = state.toLowerCase().trim().replace(/\s+/g, "-");
  return slug.slice(0, MAX_SLUG_LENGTH);
}

/** "San Francisco" → "san-francisco" */
export function cityToSlug(city: string): string {
  console.assert(typeof city === "string", "cityToSlug: city must be a string");
  console.assert(city.length > 0, "cityToSlug: city must not be empty");
  const slug = city
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
  return slug.slice(0, MAX_SLUG_LENGTH);
}

/** "new-york" → "New York" */
export function slugToState(slug: string): string | null {
  console.assert(typeof slug === "string", "slugToState: slug must be a string");
  console.assert(slug.length > 0, "slugToState: slug must not be empty");
  return SLUG_TO_STATE[slug] ?? null;
}

/**
 * "new-york" → "NY"
 * Returns null if the slug doesn't match a known state.
 */
export function slugToAbbreviation(slug: string): string | null {
  console.assert(typeof slug === "string", "slugToAbbreviation: slug must be a string");
  const name = slug.replace(/-/g, " ").toLowerCase();
  return STATE_ABBREVIATIONS[name] ?? null;
}

/**
 * "san-francisco" → "San Francisco"
 * Generic slug-to-title conversion (no lookup table needed for cities).
 */
export function slugToCity(slug: string): string {
  console.assert(typeof slug === "string", "slugToCity: slug must be a string");
  console.assert(slug.length > 0, "slugToCity: slug must not be empty");
  return slug
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
```

- [ ] **Step 2: Verify no type errors**

Run: `cd /home/chris/projects/lgs-directory/web && npx tsc --noEmit`
Expected: zero errors

- [ ] **Step 3: Commit**

```bash
cd /home/chris/projects/lgs-directory/web
git add lib/slugs.ts
git commit -m "feat: add slug utility functions for state/city URL generation"
```

---

### Task 2: New Database Queries

**Files:**
- Modify: `web/lib/queries.ts`
- Modify: `web/lib/types.ts`

- [ ] **Step 1: Add new types to `web/lib/types.ts`**

Add these at the end of the file:

```typescript
export interface StateStats {
  state: string;
  slug: string;
  store_count: number;
  active_count: number;
  wpn_premium_count: number;
  online_count: number;
}

export interface CityStats {
  city: string;
  slug: string;
  store_count: number;
  active_count: number;
  wpn_premium_count: number;
  online_count: number;
}

export interface OnlineStore {
  store_id: string;
  store_name: string;
  presence_url: string;
  channel_type: ChannelType;
  platform: Platform | null;
  estimated_inventory_size: InventorySize | null;
}
```

- [ ] **Step 2: Add `getStateIndex` query to `web/lib/queries.ts`**

Add this import at the top:

```typescript
import { stateToSlug, cityToSlug } from "@/lib/slugs";
```

And import the new types:

```typescript
import type { StateStats, CityStats, OnlineStore } from "@/lib/types";
```

Add this function:

```typescript
const MAX_STATES = 60;

export async function getStateIndex(): Promise<StateStats[]> {
  const sql = `
    SELECT
      address->>'state' as state,
      COUNT(*)::int as store_count,
      COUNT(*) FILTER (WHERE status = 'active')::int as active_count,
      COUNT(*) FILTER (WHERE wpn_level = 'premium')::int as wpn_premium_count,
      COUNT(DISTINCT CASE
        WHEN id IN (
          SELECT store_id FROM online_presences
          WHERE sells_mtg_singles = true AND status = 'active'
        ) THEN id
      END)::int as online_count
    FROM stores
    WHERE status IN ('active', 'verified', 'candidate')
      AND address->>'state' IS NOT NULL
    GROUP BY address->>'state'
    ORDER BY address->>'state'
  `;

  console.assert(typeof sql === "string", "getStateIndex: sql must be a string");

  const rows = await query<{
    state: string;
    store_count: number;
    active_count: number;
    wpn_premium_count: number;
    online_count: number;
  }>(sql);

  console.assert(Array.isArray(rows), "getStateIndex: rows must be an array");

  const results: StateStats[] = [];
  const limit = Math.min(rows.length, MAX_STATES);
  for (let i = 0; i < limit; i++) {
    const row = rows[i];
    results.push({
      ...row,
      slug: stateToSlug(row.state),
    });
  }
  return results;
}
```

- [ ] **Step 3: Add `getCityIndex` query**

```typescript
const MAX_CITIES_PER_STATE = 500;
const MIN_STORES_FOR_CITY_PAGE = 2;

export async function getCityIndex(stateDbName: string): Promise<CityStats[]> {
  console.assert(typeof stateDbName === "string", "getCityIndex: stateDbName must be a string");
  console.assert(stateDbName.length > 0, "getCityIndex: stateDbName must not be empty");

  const sql = `
    SELECT
      address->>'city' as city,
      COUNT(*)::int as store_count,
      COUNT(*) FILTER (WHERE status = 'active')::int as active_count,
      COUNT(*) FILTER (WHERE wpn_level = 'premium')::int as wpn_premium_count,
      COUNT(DISTINCT CASE
        WHEN id IN (
          SELECT store_id FROM online_presences
          WHERE sells_mtg_singles = true AND status = 'active'
        ) THEN id
      END)::int as online_count
    FROM stores
    WHERE status IN ('active', 'verified', 'candidate')
      AND UPPER(address->>'state') = UPPER($1)
      AND address->>'city' IS NOT NULL
    GROUP BY address->>'city'
    HAVING COUNT(*) >= $2
    ORDER BY address->>'city'
  `;

  const rows = await query<{
    city: string;
    store_count: number;
    active_count: number;
    wpn_premium_count: number;
    online_count: number;
  }>(sql, [stateDbName, MIN_STORES_FOR_CITY_PAGE]);

  console.assert(Array.isArray(rows), "getCityIndex: rows must be an array");

  const results: CityStats[] = [];
  const limit = Math.min(rows.length, MAX_CITIES_PER_STATE);
  for (let i = 0; i < limit; i++) {
    const row = rows[i];
    results.push({
      ...row,
      slug: cityToSlug(row.city),
    });
  }
  return results;
}
```

- [ ] **Step 4: Add `getOnlineStores` query**

```typescript
const MAX_ONLINE_STORES = 100;

export async function getOnlineStores(
  stateDbName: string,
  cityDbName?: string
): Promise<OnlineStore[]> {
  console.assert(typeof stateDbName === "string", "getOnlineStores: stateDbName must be a string");
  console.assert(stateDbName.length > 0, "getOnlineStores: stateDbName must not be empty");

  const conditions = [
    "s.status IN ('active', 'verified', 'candidate')",
    "UPPER(s.address->>'state') = UPPER($1)",
    "op.sells_mtg_singles = true",
    "op.status = 'active'",
  ];
  const params: unknown[] = [stateDbName];

  if (cityDbName) {
    params.push(cityDbName);
    conditions.push(`UPPER(s.address->>'city') = UPPER($${params.length})`);
  }

  const sql = `
    SELECT
      s.id as store_id,
      s.name as store_name,
      op.url as presence_url,
      op.channel_type,
      op.platform,
      op.estimated_inventory_size
    FROM stores s
    JOIN online_presences op ON op.store_id = s.id
    WHERE ${conditions.join(" AND ")}
    ORDER BY s.name
    LIMIT $${params.length + 1}
  `;
  params.push(MAX_ONLINE_STORES);

  const rows = await query<OnlineStore>(sql, params);
  console.assert(Array.isArray(rows), "getOnlineStores: rows must be an array");
  return rows;
}
```

- [ ] **Step 5: Add `getNearbyCities` query**

```typescript
const MAX_NEARBY_CITIES = 8;

export async function getNearbyCities(
  stateDbName: string,
  cityDbName: string,
  limit: number = MAX_NEARBY_CITIES
): Promise<CityStats[]> {
  console.assert(typeof stateDbName === "string", "getNearbyCities: stateDbName must be a string");
  console.assert(typeof cityDbName === "string", "getNearbyCities: cityDbName must be a string");

  const boundedLimit = Math.min(limit, MAX_NEARBY_CITIES);

  const sql = `
    SELECT
      address->>'city' as city,
      COUNT(*)::int as store_count,
      COUNT(*) FILTER (WHERE status = 'active')::int as active_count,
      COUNT(*) FILTER (WHERE wpn_level = 'premium')::int as wpn_premium_count,
      COUNT(DISTINCT CASE
        WHEN id IN (
          SELECT store_id FROM online_presences
          WHERE sells_mtg_singles = true AND status = 'active'
        ) THEN id
      END)::int as online_count
    FROM stores
    WHERE status IN ('active', 'verified', 'candidate')
      AND UPPER(address->>'state') = UPPER($1)
      AND UPPER(address->>'city') != UPPER($2)
      AND address->>'city' IS NOT NULL
    GROUP BY address->>'city'
    HAVING COUNT(*) >= 2
    ORDER BY COUNT(*) DESC
    LIMIT $3
  `;

  const rows = await query<{
    city: string;
    store_count: number;
    active_count: number;
    wpn_premium_count: number;
    online_count: number;
  }>(sql, [stateDbName, cityDbName, boundedLimit]);

  console.assert(Array.isArray(rows), "getNearbyCities: rows must be an array");

  const results: CityStats[] = [];
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    results.push({
      ...row,
      slug: cityToSlug(row.city),
    });
  }
  return results;
}
```

- [ ] **Step 6: Extend `listStores` to accept city filter**

In the existing `ListStoresParams` interface, add:

```typescript
city?: string;
```

In the existing `listStores` function body, after the `state` filter block, add:

```typescript
if (params.city) {
  paramIndex++;
  conditions.push(`UPPER(address->>'city') = UPPER($${paramIndex})`);
  values.push(params.city);
}
```

- [ ] **Step 7: Verify no type errors**

Run: `cd /home/chris/projects/lgs-directory/web && npx tsc --noEmit`
Expected: zero errors

- [ ] **Step 8: Commit**

```bash
cd /home/chris/projects/lgs-directory/web
git add lib/queries.ts lib/types.ts
git commit -m "feat: add state/city aggregation queries and online stores query"
```

---

### Task 3: Shared SEO Components

**Files:**
- Create: `web/components/seo/json-ld.tsx`
- Create: `web/components/seo/breadcrumb.tsx`
- Create: `web/components/stats-bar.tsx`
- Create: `web/components/nearby-cities.tsx`

- [ ] **Step 1: Create JsonLd component**

```typescript
// web/components/seo/json-ld.tsx

interface JsonLdProps {
  data: Record<string, unknown>;
}

export function JsonLd({ data }: Readonly<JsonLdProps>) {
  console.assert(data !== null && typeof data === "object", "JsonLd: data must be an object");
  console.assert("@context" in data, "JsonLd: data must include @context");

  // Note: data is constructed from our own DB, not user input — safe for serialization.
  // If this ever accepts external input, sanitize first.
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
```

- [ ] **Step 2: Create Breadcrumb component**

```typescript
// web/components/seo/breadcrumb.tsx
import Link from "next/link";
import { JsonLd } from "@/components/seo/json-ld";

export interface BreadcrumbItem {
  name: string;
  href: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  baseUrl?: string;
}

const MAX_BREADCRUMB_ITEMS = 10;

export function Breadcrumb({
  items,
  baseUrl = "https://lgs-directory.com",
}: Readonly<BreadcrumbProps>) {
  console.assert(Array.isArray(items), "Breadcrumb: items must be an array");
  console.assert(items.length > 0, "Breadcrumb: items must not be empty");

  const boundedItems = items.slice(0, MAX_BREADCRUMB_ITEMS);

  const jsonLdData = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: boundedItems.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: `${baseUrl}${item.href}`,
    })),
  };

  return (
    <>
      <JsonLd data={jsonLdData} />
      <nav aria-label="Breadcrumb" className="mb-4">
        <ol className="flex items-center gap-1.5 text-sm text-zinc-500">
          {boundedItems.map((item, index) => {
            const isLast = index === boundedItems.length - 1;
            return (
              <li key={item.href} className="flex items-center gap-1.5">
                {index > 0 && <span aria-hidden="true">→</span>}
                {isLast ? (
                  <span className="text-zinc-300">{item.name}</span>
                ) : (
                  <Link
                    href={item.href}
                    className="hover:text-zinc-300 transition-colors"
                  >
                    {item.name}
                  </Link>
                )}
              </li>
            );
          })}
        </ol>
      </nav>
    </>
  );
}
```

- [ ] **Step 3: Create StatsBar component**

```typescript
// web/components/stats-bar.tsx

interface StatsBarProps {
  storeCount: number;
  activeCount: number;
  wpnPremiumCount: number;
  onlineCount: number;
}

export function StatsBar({
  storeCount,
  activeCount,
  wpnPremiumCount,
  onlineCount,
}: Readonly<StatsBarProps>) {
  console.assert(storeCount >= 0, "StatsBar: storeCount must be non-negative");
  console.assert(activeCount >= 0, "StatsBar: activeCount must be non-negative");

  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1 text-sm text-zinc-400 mb-4">
      <span>{storeCount} stores</span>
      <span className="text-zinc-600">·</span>
      <span className="text-emerald-400">{activeCount} active</span>
      <span className="text-zinc-600">·</span>
      <span className="text-purple-400">{wpnPremiumCount} WPN Premium</span>
      <span className="text-zinc-600">·</span>
      <span className="text-blue-400">{onlineCount} sell online</span>
    </div>
  );
}
```

- [ ] **Step 4: Create NearbyCities component**

```typescript
// web/components/nearby-cities.tsx
import Link from "next/link";
import type { CityStats } from "@/lib/types";

interface NearbyCitiesProps {
  stateSlug: string;
  cities: CityStats[];
}

const MAX_DISPLAY = 8;

export function NearbyCities({ stateSlug, cities }: Readonly<NearbyCitiesProps>) {
  console.assert(typeof stateSlug === "string", "NearbyCities: stateSlug must be a string");
  console.assert(Array.isArray(cities), "NearbyCities: cities must be an array");

  if (cities.length === 0) {
    return null;
  }

  const displayed = cities.slice(0, MAX_DISPLAY);

  return (
    <div>
      <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-3">
        Nearby Cities
      </h2>
      <div className="flex flex-wrap gap-2">
        {displayed.map((city) => (
          <Link
            key={city.slug}
            href={`/stores/${stateSlug}/${city.slug}`}
            className="rounded-md bg-zinc-800 px-3 py-1.5 text-sm text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200 transition-colors"
          >
            {city.city} ({city.store_count})
          </Link>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Verify no type errors**

Run: `cd /home/chris/projects/lgs-directory/web && npx tsc --noEmit`
Expected: zero errors

- [ ] **Step 6: Commit**

```bash
cd /home/chris/projects/lgs-directory/web
git add components/seo/ components/stats-bar.tsx components/nearby-cities.tsx
git commit -m "feat: add SEO and shared components (JsonLd, Breadcrumb, StatsBar, NearbyCities)"
```

---

### Task 4: OnlineStoresCard Component

**Files:**
- Create: `web/components/online-stores-card.tsx`

- [ ] **Step 1: Create OnlineStoresCard component**

```typescript
// web/components/online-stores-card.tsx
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { formatPlatform } from "@/lib/format";
import type { OnlineStore } from "@/lib/types";

interface OnlineStoresCardProps {
  stores: OnlineStore[];
}

const MAX_DISPLAY = 20;

const INVENTORY_LABELS: Record<string, string> = {
  small: "Small",
  medium: "Medium",
  large: "Large",
};

export function OnlineStoresCard({ stores }: Readonly<OnlineStoresCardProps>) {
  console.assert(Array.isArray(stores), "OnlineStoresCard: stores must be an array");
  console.assert(stores.length >= 0, "OnlineStoresCard: stores must be non-negative length");

  if (stores.length === 0) {
    return null;
  }

  const displayed = stores.slice(0, MAX_DISPLAY);

  return (
    <div>
      <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-3">
        Buy Cards Online
      </h2>
      <div className="rounded-lg border border-zinc-800 bg-zinc-950 divide-y divide-zinc-800">
        {displayed.map((store) => (
          <div
            key={`${store.store_id}-${store.presence_url}`}
            className="flex items-center justify-between px-4 py-3"
          >
            <div className="flex flex-col gap-1 min-w-0">
              <Link
                href={`/stores/${store.store_id}`}
                className="text-sm font-medium text-zinc-200 hover:text-white transition-colors truncate"
              >
                {store.store_name}
              </Link>
              <div className="flex items-center gap-2 text-xs text-zinc-500">
                {store.platform && (
                  <span>{formatPlatform(store.platform)}</span>
                )}
                {store.estimated_inventory_size &&
                  store.estimated_inventory_size !== "none" && (
                    <span>
                      · {INVENTORY_LABELS[store.estimated_inventory_size] ?? store.estimated_inventory_size} inventory
                    </span>
                  )}
              </div>
            </div>
            <a
              href={store.presence_url}
              target="_blank"
              rel="nofollow sponsored noopener"
              className="flex-shrink-0 ml-3"
            >
              <Badge
                variant="outline"
                className="text-blue-400 border-blue-400/30 hover:bg-blue-400/10 cursor-pointer"
              >
                Visit Shop ↗
              </Badge>
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify no type errors**

Run: `cd /home/chris/projects/lgs-directory/web && npx tsc --noEmit`
Expected: zero errors

- [ ] **Step 3: Commit**

```bash
cd /home/chris/projects/lgs-directory/web
git add components/online-stores-card.tsx
git commit -m "feat: add OnlineStoresCard component for buy-cards-online section"
```

---

### Task 5: CityGrid Component

**Files:**
- Create: `web/components/city-grid.tsx`

- [ ] **Step 1: Create CityGrid component**

```typescript
// web/components/city-grid.tsx
import Link from "next/link";
import type { CityStats } from "@/lib/types";

interface CityGridProps {
  stateSlug: string;
  cities: CityStats[];
}

const MAX_DISPLAY = 500;

export function CityGrid({ stateSlug, cities }: Readonly<CityGridProps>) {
  console.assert(typeof stateSlug === "string", "CityGrid: stateSlug must be a string");
  console.assert(Array.isArray(cities), "CityGrid: cities must be an array");

  if (cities.length === 0) {
    return (
      <p className="text-sm text-zinc-500">No cities with multiple stores found.</p>
    );
  }

  const displayed = cities.slice(0, MAX_DISPLAY);

  return (
    <div>
      <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-3">
        Browse by City
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
        {displayed.map((city) => (
          <Link
            key={city.slug}
            href={`/stores/${stateSlug}/${city.slug}`}
            className="rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-800 hover:text-white transition-colors"
          >
            <span className="block truncate">{city.city}</span>
            <span className="text-xs text-zinc-500">{city.store_count} stores</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify no type errors**

Run: `cd /home/chris/projects/lgs-directory/web && npx tsc --noEmit`
Expected: zero errors

- [ ] **Step 3: Commit**

```bash
cd /home/chris/projects/lgs-directory/web
git add components/city-grid.tsx
git commit -m "feat: add CityGrid component for state page city listing"
```

---

### Task 6: State Page

**Files:**
- Create: `web/app/stores/[state]/page.tsx`

- [ ] **Step 1: Create the state page**

Read existing pages (`web/app/page.tsx` and `web/app/stores/[id]/page.tsx`) to match patterns exactly.

Create `web/app/stores/[state]/page.tsx` with:
- `generateMetadata` returning title "Game Stores in {State} | LGS Directory" with description and OpenGraph
- `generateStaticParams` calling `getStateIndex()` to return all state slugs
- `export const revalidate = 86400` for 24-hour ISR
- Page component that:
  1. Resolves `params.state` slug via `slugToState()`
  2. Calls `notFound()` if slug doesn't match a known state
  3. Fetches `listStores({ state, page })` and `getCityIndex(state)` in parallel via `Promise.all`
  4. Clamps page to valid range (same pattern as existing `page.tsx`)
  5. Renders: `Breadcrumb` → `h1` → `StatsBar` → `StoreMap` (dynamic, ssr:false) → `CityGrid` → `StoreTable` + `Pagination` → `JsonLd` (ItemList of LocalBusiness)

The `StoreMap` component expects `StoreWithDistance[]` — map stores by adding `distance_miles: 0` to each store that has coordinates. Use the first store's coordinates as the `userLat`/`userLng` center point.

See the spec file at `docs/superpowers/specs/2026-04-02-programmatic-seo-pages-design.md` "State Page" section for the exact layout order and JSON-LD schema structure.

- [ ] **Step 2: Verify no type errors**

Run: `cd /home/chris/projects/lgs-directory/web && npx tsc --noEmit`
Expected: zero errors

- [ ] **Step 3: Test manually**

Open `http://localhost:3000/stores/texas` in the browser. Verify:
- Breadcrumb shows "Home → Texas"
- Stats bar shows store counts
- City grid shows cities with links
- Store table renders with pagination
- Map shows store pins

- [ ] **Step 4: Commit**

```bash
cd /home/chris/projects/lgs-directory/web
git add app/stores/\[state\]/page.tsx
git commit -m "feat: add state page with city grid, map, stats, and structured data"
```

---

### Task 7: City Page

**Files:**
- Create: `web/app/stores/[state]/[city]/page.tsx`

- [ ] **Step 1: Create the city page**

Read the state page from Task 6 to match patterns.

Create `web/app/stores/[state]/[city]/page.tsx` with:
- `generateMetadata` returning title "Game Stores in {City}, {Abbrev} | LGS Directory"
- `export const revalidate = 86400` for 24-hour ISR
- Page component that:
  1. Resolves `params.state` and `params.city` slugs
  2. Calls `notFound()` if state slug invalid
  3. Fetches `listStores({ state, city, page })`, `getOnlineStores(state, city)`, and `getNearbyCities(state, city)` in parallel
  4. Calls `notFound()` if `storeResult.total === 0` (no stores in this city)
  5. Clamps page to valid range
  6. Renders table-first layout: `Breadcrumb` → `h1` → `StatsBar` → `StoreTable` + `Pagination` → two-column grid (`StoreMap` left, `OnlineStoresCard` right) → `NearbyCities` → `JsonLd`

Stats (activeCount, premiumCount) computed from the store results inline rather than a separate query.

See spec "City Page" section for exact layout and JSON-LD structure.

- [ ] **Step 2: Verify no type errors**

Run: `cd /home/chris/projects/lgs-directory/web && npx tsc --noEmit`
Expected: zero errors

- [ ] **Step 3: Test manually**

Open `http://localhost:3000/stores/texas/austin` (adjust city to one in your data). Verify:
- Breadcrumb: Home → Texas → Austin
- Stats bar renders
- Store table populated
- Map shows pins
- "Buy Cards Online" section shows online stores
- Nearby cities links appear

- [ ] **Step 4: Commit**

```bash
cd /home/chris/projects/lgs-directory/web
git add app/stores/\[state\]/\[city\]/page.tsx
git commit -m "feat: add city page with store table, map, online shops, and nearby cities"
```

---

### Task 8: Homepage State Links

**Files:**
- Modify: `web/app/page.tsx`

- [ ] **Step 1: Add state directory to homepage**

Read `web/app/page.tsx` first. Then:

1. Import `getStateIndex` from `@/lib/queries` and `Link` from `next/link`
2. Add `getStateIndex()` to the existing `Promise.all` data fetch
3. After the `Pagination` component, add a "Browse by State" section:

```tsx
{states.length > 0 && (
  <div className="mt-12 border-t border-zinc-800 pt-8">
    <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-3">
      Browse by State
    </h2>
    <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
      {states.map((s) => (
        <Link
          key={s.slug}
          href={`/stores/${s.slug}`}
          className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          {s.state} ({s.store_count})
        </Link>
      ))}
    </div>
  </div>
)}
```

- [ ] **Step 2: Verify no type errors**

Run: `cd /home/chris/projects/lgs-directory/web && npx tsc --noEmit`
Expected: zero errors

- [ ] **Step 3: Commit**

```bash
cd /home/chris/projects/lgs-directory/web
git add app/page.tsx
git commit -m "feat: add state directory links to homepage for internal linking"
```

---

### Task 9: Sitemap, robots.txt, and llms.txt

**Files:**
- Create: `web/app/sitemap.ts`
- Create: `web/app/robots.ts`
- Create: `web/app/llms.txt/route.ts`

- [ ] **Step 1: Create dynamic sitemap**

Create `web/app/sitemap.ts` using Next.js `MetadataRoute.Sitemap` return type. The function should:

1. Start with the homepage entry (priority 1.0, weekly)
2. Query all distinct states from stores table (active/verified/candidate, non-null state)
3. Add state page entries with `stateToSlug()` (priority 0.8, weekly)
4. Query all state+city pairs with 2+ stores (active/verified/candidate)
5. Add city page entries with `stateToSlug()`/`cityToSlug()` (priority 0.6, weekly)
6. Query all store IDs (active/verified/candidate)
7. Add store detail entries (priority 0.4, monthly)

Use `BASE_URL = "https://lgs-directory.com"` and `MAX_SITEMAP_ENTRIES = 50000`.

Import `query` from `@/lib/db` and slug functions from `@/lib/slugs`.

- [ ] **Step 2: Create robots.ts**

Create `web/app/robots.ts` returning `MetadataRoute.Robots`:
- Allow all user agents on all paths
- Sitemap URL: `https://lgs-directory.com/sitemap.xml`

- [ ] **Step 3: Create llms.txt route handler**

Create `web/app/llms.txt/route.ts` with a `GET` handler that returns the plain text content from the spec's `/llms.txt` section. Set `Content-Type: text/plain; charset=utf-8` and `Cache-Control: public, max-age=86400`.

- [ ] **Step 4: Verify no type errors**

Run: `cd /home/chris/projects/lgs-directory/web && npx tsc --noEmit`
Expected: zero errors

- [ ] **Step 5: Test manually**

- `http://localhost:3000/sitemap.xml` — valid XML with state, city, and store URLs
- `http://localhost:3000/robots.txt` — allow rules + sitemap URL
- `http://localhost:3000/llms.txt` — plain text site description

- [ ] **Step 6: Commit**

```bash
cd /home/chris/projects/lgs-directory/web
git add app/sitemap.ts app/robots.ts app/llms.txt/
git commit -m "feat: add dynamic sitemap, robots.txt, and llms.txt"
```

---

### Task 10: Store Detail Breadcrumb

**Files:**
- Modify: `web/app/stores/[id]/page.tsx`

- [ ] **Step 1: Replace BackButton with Breadcrumb**

Read `web/app/stores/[id]/page.tsx` first. Then:

1. Add imports for `Breadcrumb` from `@/components/seo/breadcrumb` and `stateToSlug`, `cityToSlug` from `@/lib/slugs`
2. Remove the `BackButton` import
3. Replace `<BackButton />` with:

```tsx
<Breadcrumb
  items={[
    { name: "Home", href: "/" },
    {
      name: store.address.state,
      href: `/stores/${stateToSlug(store.address.state)}`,
    },
    {
      name: store.address.city,
      href: `/stores/${stateToSlug(store.address.state)}/${cityToSlug(store.address.city)}`,
    },
    { name: store.name, href: `/stores/${store.id}` },
  ]}
/>
```

- [ ] **Step 2: Verify no type errors**

Run: `cd /home/chris/projects/lgs-directory/web && npx tsc --noEmit`
Expected: zero errors

- [ ] **Step 3: Commit**

```bash
cd /home/chris/projects/lgs-directory/web
git add app/stores/\[id\]/page.tsx
git commit -m "feat: replace back button with breadcrumb on store detail page"
```

---

### Task 11: Final Verification

- [ ] **Step 1: Full type check**

Run: `cd /home/chris/projects/lgs-directory/web && npx tsc --noEmit`
Expected: zero errors

- [ ] **Step 2: Lint check**

Run: `cd /home/chris/projects/lgs-directory/web && npx eslint .`
Expected: zero errors (pre-existing warnings acceptable)

- [ ] **Step 3: Smoke test all new routes**

Navigate to each and verify no errors:
- `http://localhost:3000/` — homepage with state links at bottom
- `http://localhost:3000/stores/texas` — state page
- `http://localhost:3000/stores/texas/austin` — city page (adjust to a real city in your data)
- `http://localhost:3000/stores/<valid-id>` — store detail with breadcrumb
- `http://localhost:3000/sitemap.xml` — valid XML
- `http://localhost:3000/robots.txt` — crawl rules
- `http://localhost:3000/llms.txt` — plain text
- `http://localhost:3000/stores/nonexistent-state` — 404

- [ ] **Step 4: Stage all changes**

```bash
cd /home/chris/projects/lgs-directory/web
git add .
```
