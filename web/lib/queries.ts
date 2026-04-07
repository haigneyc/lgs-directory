import { cache } from "react";
import { query } from "./db";
import { stateToSlug, cityToSlug } from "@/lib/slugs";
import type {
  Store,
  StoreWithPresences,
  StoreWithDistance,
  OnlinePresence,
  StateStats,
  CityStats,
  OnlineStore,
  StoreEnrichment,
  StoreContent,
  StoreCategory,
  HoursPeriod,
} from "./types";

const PAGE_SIZE = 25;

/**
 * SQL fragment that filters out unverified candidate stores.
 * Candidate stores are hidden unless they have a trusted external ref
 * (WPN registration or content scraper that found game products).
 * This prevents low-quality Google Places-only candidates from appearing.
 */
const TRUSTED_CANDIDATE_FILTER = `
  AND NOT (
    status = 'candidate'
    AND wpn_id IS NULL
    AND id NOT IN (
      SELECT store_id FROM store_external_refs
      WHERE provider = 'website_content'
        AND jsonb_array_length(COALESCE(payload->'products', '[]'::jsonb)) > 0
    )
  )
`;

interface ListStoresParams {
  page?: number;
  state?: string;
  city?: string;
  status?: string;
  wpnLevel?: string;
  sellsSingles?: boolean;
  search?: string;
  category?: string;
  game?: string;
}

interface ListStoresResult {
  stores: Store[];
  total: number;
  page: number;
  pageSize: number;
}

export async function listStores(
  params: ListStoresParams
): Promise<ListStoresResult> {
  const page = params.page ?? 1;
  const offset = (page - 1) * PAGE_SIZE;

  // Always filter out closed/removed stores; allow explicit status override
  const conditions: string[] = [];
  const values: unknown[] = [];
  let idx = 1;

  if (params.status) {
    conditions.push(`status = $${idx++}`);
    values.push(params.status);
  } else {
    conditions.push(`status IN ('active', 'verified', 'candidate')`);
  }

  if (params.state) {
    conditions.push(`address->>'state' = $${idx++}`);
    values.push(params.state.toUpperCase());
  }
  if (params.city) {
    conditions.push(`UPPER(address->>'city') = UPPER($${idx++})`);
    values.push(params.city);
  }
  if (params.wpnLevel) {
    conditions.push(`wpn_level = $${idx++}`);
    values.push(params.wpnLevel);
  }
  if (params.sellsSingles !== undefined) {
    conditions.push(`id IN (
      SELECT store_id FROM online_presences
      WHERE sells_mtg_singles = $${idx++}
    )`);
    values.push(params.sellsSingles);
  }
  if (params.search) {
    conditions.push(`name ILIKE $${idx++}`);
    values.push(`%${params.search}%`);
  }
  if (params.category) {
    conditions.push(`id IN (
      SELECT store_id FROM store_categories
      WHERE category = $${idx++}
    )`);
    values.push(params.category);
  }
  if (params.game) {
    conditions.push(`id IN (
      SELECT store_id FROM store_external_refs
      WHERE provider = 'website_content'
        AND payload->'products' ? $${idx++}
    )`);
    values.push(params.game);
  }

  const where = `WHERE ${conditions.join(" AND ")}`;

  const countRows = await query<{ total: number }>(
    `SELECT count(*)::int as total FROM stores ${where} ${TRUSTED_CANDIDATE_FILTER}`,
    values
  );
  const total = countRows[0]?.total ?? 0;

  const stores = await query<Store>(
    `SELECT * FROM stores ${where} ${TRUSTED_CANDIDATE_FILTER}
     ORDER BY name ASC
     LIMIT $${idx++} OFFSET $${idx++}`,
    [...values, PAGE_SIZE, offset]
  );

  return { stores, total, page, pageSize: PAGE_SIZE };
}

/**
 * Fetch a store with its online presences. Wrapped with React `cache()` so
 * that repeated calls within the same request (e.g. `generateMetadata` +
 * default export on `/store/[id]`) dedupe to a single pair of DB round-trips.
 * Per-request memoization only — does not persist across requests.
 */
export const getStore = cache(async (
  id: string
): Promise<StoreWithPresences | null> => {
  console.assert(typeof id === "string", "getStore: id must be a string");
  console.assert(id.length > 0, "getStore: id must be non-empty");

  const storeRows = await query<Store>(
    "SELECT * FROM stores WHERE id = $1",
    [id]
  );
  if (storeRows.length === 0) {
    return null;
  }

  const presences = await query<OnlinePresence>(
    `SELECT * FROM online_presences
     WHERE store_id = $1
     ORDER BY channel_type, url`,
    [id]
  );

  return { ...storeRows[0], presences };
});

export async function getNearbyStores(
  lat: number,
  lng: number,
  radiusMiles: number,
  limit: number = 50
): Promise<StoreWithDistance[]> {
  // Bounding box pre-filter (1 degree lat ~ 69 miles)
  const latDelta = radiusMiles / 69.0;
  const lngDelta = radiusMiles / (69.0 * Math.cos((lat * Math.PI) / 180));

  const rows = await query<StoreWithDistance>(
    `SELECT *,
      (3958.8 * acos(
        LEAST(1.0, GREATEST(-1.0,
          cos(radians($1)) * cos(radians(latitude)) *
          cos(radians(longitude) - radians($2)) +
          sin(radians($1)) * sin(radians(latitude))
        ))
      )) AS distance_miles
     FROM stores
     WHERE latitude IS NOT NULL
       AND longitude IS NOT NULL
       AND status IN ('active', 'verified', 'candidate')
       ${TRUSTED_CANDIDATE_FILTER}
       AND latitude BETWEEN $3 AND $4
       AND longitude BETWEEN $5 AND $6
     ORDER BY distance_miles
     LIMIT $7`,
    [lat, lng, lat - latDelta, lat + latDelta, lng - lngDelta, lng + lngDelta, limit]
  );

  // Post-filter by exact Haversine radius (bounding box is approximate)
  return rows.filter((r) => r.distance_miles <= radiusMiles);
}

export async function getFilterOptions(): Promise<{
  states: string[];
  statuses: string[];
  wpnLevels: string[];
  categories: string[];
}> {
  const [stateRows, statusRows, wpnRows, categoryRows] = await Promise.all([
    query<{ state: string }>(
      `SELECT DISTINCT address->>'state' as state FROM stores
       WHERE address->>'state' IS NOT NULL
       ORDER BY state`
    ),
    query<{ status: string }>(
      "SELECT DISTINCT status FROM stores ORDER BY status"
    ),
    query<{ wpn_level: string }>(
      `SELECT DISTINCT wpn_level FROM stores
       WHERE wpn_level IS NOT NULL
       ORDER BY wpn_level`
    ),
    query<{ category: string }>(
      `SELECT DISTINCT category FROM store_categories ORDER BY category`
    ).catch(() => [] as { category: string }[]),
  ]);

  return {
    states: stateRows.map((r) => r.state),
    statuses: statusRows.map((r) => r.status),
    wpnLevels: wpnRows.map((r) => r.wpn_level),
    categories: categoryRows.map((r) => r.category),
  };
}

export async function getStateIndex(): Promise<StateStats[]> {
  const rows = await query<{
    state: string;
    store_count: number;
    active_count: number;
    wpn_premium_count: number;
    online_count: number;
  }>(
    `SELECT
       address->>'state' AS state,
       COUNT(*)::int AS store_count,
       COUNT(*) FILTER (WHERE status IN ('active', 'verified'))::int AS active_count,
       COUNT(*) FILTER (WHERE wpn_level = 'premium')::int AS wpn_premium_count,
       COUNT(*) FILTER (WHERE id IN (
         SELECT op.store_id FROM online_presences op
         WHERE op.sells_mtg_singles = true AND op.status = 'active'
       ))::int AS online_count
     FROM stores
     WHERE status IN ('active', 'verified', 'candidate')
       ${TRUSTED_CANDIDATE_FILTER}
       AND address->>'state' IS NOT NULL
     GROUP BY address->>'state'
     ORDER BY store_count DESC`
  );

  console.assert(Array.isArray(rows), "getStateIndex: rows must be an array");
  console.assert(rows.length >= 0, "getStateIndex: rows length must be non-negative");

  const result: StateStats[] = [];
  const limit = Math.min(rows.length, 60);
  for (let i = 0; i < limit; i++) {
    const row = rows[i];
    console.assert(typeof row.state === "string", "getStateIndex: state must be a string");
    result.push({
      state: row.state,
      slug: stateToSlug(row.state),
      store_count: row.store_count,
      active_count: row.active_count,
      wpn_premium_count: row.wpn_premium_count,
      online_count: row.online_count,
    });
  }

  return result;
}

export async function getCityIndex(stateDbName: string): Promise<CityStats[]> {
  console.assert(typeof stateDbName === "string", "getCityIndex: stateDbName must be a string");
  console.assert(stateDbName.length > 0, "getCityIndex: stateDbName must not be empty");

  const rows = await query<{
    city: string;
    store_count: number;
    active_count: number;
    wpn_premium_count: number;
    online_count: number;
  }>(
    `SELECT
       address->>'city' AS city,
       COUNT(*)::int AS store_count,
       COUNT(*) FILTER (WHERE status IN ('active', 'verified'))::int AS active_count,
       COUNT(*) FILTER (WHERE wpn_level = 'premium')::int AS wpn_premium_count,
       COUNT(*) FILTER (WHERE id IN (
         SELECT op.store_id FROM online_presences op
         WHERE op.sells_mtg_singles = true AND op.status = 'active'
       ))::int AS online_count
     FROM stores
     WHERE status IN ('active', 'verified', 'candidate')
       ${TRUSTED_CANDIDATE_FILTER}
       AND UPPER(address->>'state') = UPPER($1)
       AND address->>'city' IS NOT NULL
     GROUP BY address->>'city'
     HAVING COUNT(*) >= 2
     ORDER BY store_count DESC`,
    [stateDbName]
  );

  console.assert(Array.isArray(rows), "getCityIndex: rows must be an array");

  const result: CityStats[] = [];
  const limit = Math.min(rows.length, 2000);
  for (let i = 0; i < limit; i++) {
    const row = rows[i];
    console.assert(typeof row.city === "string", "getCityIndex: city must be a string");
    result.push({
      city: row.city,
      slug: cityToSlug(row.city),
      store_count: row.store_count,
      active_count: row.active_count,
      wpn_premium_count: row.wpn_premium_count,
      online_count: row.online_count,
    });
  }

  return result;
}

export async function getOnlineStores(
  stateDbName: string,
  cityDbName?: string
): Promise<OnlineStore[]> {
  console.assert(typeof stateDbName === "string", "getOnlineStores: stateDbName must be a string");
  console.assert(stateDbName.length > 0, "getOnlineStores: stateDbName must not be empty");

  const conditions: string[] = [
    "UPPER(s.address->>'state') = UPPER($1)",
    "op.sells_mtg_singles = true",
  ];
  const values: unknown[] = [stateDbName];
  let idx = 2;

  if (cityDbName !== undefined) {
    console.assert(typeof cityDbName === "string", "getOnlineStores: cityDbName must be a string");
    conditions.push(`UPPER(s.address->>'city') = UPPER($${idx++})`);
    values.push(cityDbName);
  }

  const where = `WHERE ${conditions.join(" AND ")}`;

  const rows = await query<OnlineStore>(
    `SELECT
       s.id AS store_id,
       s.name AS store_name,
       op.url AS presence_url,
       op.channel_type,
       op.platform,
       op.estimated_inventory_size
     FROM stores s
     JOIN online_presences op ON op.store_id = s.id
     ${where}
     ORDER BY s.name ASC`,
    values
  );

  console.assert(Array.isArray(rows), "getOnlineStores: rows must be an array");
  console.assert(rows.length >= 0, "getOnlineStores: rows length must be non-negative");

  return rows;
}

export async function getCityDescription(
  state: string,
  city: string
): Promise<string | null> {
  console.assert(typeof state === "string" && state.length > 0, "getCityDescription: state must be a non-empty string");
  console.assert(typeof city === "string" && city.length > 0, "getCityDescription: city must be a non-empty string");

  try {
    const rows = await query<{ description: string }>(
      `SELECT description FROM city_descriptions
       WHERE UPPER(state) = UPPER($1) AND UPPER(city) = UPPER($2)
       LIMIT 1`,
      [state, city]
    );

    console.assert(Array.isArray(rows), "getCityDescription: rows must be an array");
    console.assert(rows.length <= 1, "getCityDescription: expected at most one row");

    if (rows.length === 0) {
      return null;
    }

    return rows[0].description;
  } catch {
    // Table may not exist yet — degrade gracefully
    return null;
  }
}

export async function getNearbyCities(
  stateDbName: string,
  cityDbName: string,
  limit = 8
): Promise<CityStats[]> {
  console.assert(typeof stateDbName === "string", "getNearbyCities: stateDbName must be a string");
  console.assert(stateDbName.length > 0, "getNearbyCities: stateDbName must not be empty");
  console.assert(typeof cityDbName === "string", "getNearbyCities: cityDbName must be a string");
  console.assert(cityDbName.length > 0, "getNearbyCities: cityDbName must not be empty");

  const rows = await query<{
    city: string;
    store_count: number;
    active_count: number;
    wpn_premium_count: number;
    online_count: number;
  }>(
    `SELECT
       address->>'city' AS city,
       COUNT(*)::int AS store_count,
       COUNT(*) FILTER (WHERE status IN ('active', 'verified'))::int AS active_count,
       COUNT(*) FILTER (WHERE wpn_level = 'premium')::int AS wpn_premium_count,
       COUNT(*) FILTER (WHERE id IN (
         SELECT op.store_id FROM online_presences op
         WHERE op.sells_mtg_singles = true AND op.status = 'active'
       ))::int AS online_count
     FROM stores
     WHERE status IN ('active', 'verified', 'candidate')
       ${TRUSTED_CANDIDATE_FILTER}
       AND UPPER(address->>'state') = UPPER($1)
       AND UPPER(address->>'city') != UPPER($2)
       AND address->>'city' IS NOT NULL
     GROUP BY address->>'city'
     ORDER BY store_count DESC
     LIMIT $3`,
    [stateDbName, cityDbName, limit]
  );

  console.assert(Array.isArray(rows), "getNearbyCities: rows must be an array");

  const result: CityStats[] = [];
  const rowLimit = Math.min(rows.length, limit);
  for (let i = 0; i < rowLimit; i++) {
    const row = rows[i];
    console.assert(typeof row.city === "string", "getNearbyCities: city must be a string");
    result.push({
      city: row.city,
      slug: cityToSlug(row.city),
      store_count: row.store_count,
      active_count: row.active_count,
      wpn_premium_count: row.wpn_premium_count,
      online_count: row.online_count,
    });
  }

  return result;
}

function isValidTimepoint(
  tp: unknown
): tp is { day: number; hour: number; minute: number } {
  if (typeof tp !== "object" || tp === null) {
    return false;
  }
  const obj = tp as Record<string, unknown>;
  const dayValid =
    typeof obj.day === "number" && obj.day >= 0 && obj.day <= 6;
  const hourValid =
    typeof obj.hour === "number" && obj.hour >= 0 && obj.hour <= 23;
  const minuteValid =
    typeof obj.minute === "number" && obj.minute >= 0 && obj.minute <= 59;
  return dayValid && hourValid && minuteValid;
}

function parsePeriods(rawPeriods: unknown): HoursPeriod[] | null {
  console.assert(
    rawPeriods === undefined || rawPeriods === null || Array.isArray(rawPeriods),
    "parsePeriods: rawPeriods must be an array, null, or undefined"
  );

  if (!Array.isArray(rawPeriods)) {
    return null;
  }

  const result: HoursPeriod[] = [];
  const limit = Math.min(rawPeriods.length, 14);
  for (let i = 0; i < limit; i++) {
    const entry = rawPeriods[i] as Record<string, unknown>;
    if (isValidTimepoint(entry.open) && isValidTimepoint(entry.close)) {
      result.push({
        open: { day: entry.open.day, hour: entry.open.hour, minute: entry.open.minute },
        close: { day: entry.close.day, hour: entry.close.hour, minute: entry.close.minute },
      });
    }
  }

  console.assert(
    result.length <= 14,
    "parsePeriods: result should have at most 14 periods"
  );

  return result.length > 0 ? result : null;
}

function parseEnrichmentPayload(
  payload: Record<string, unknown>
): StoreEnrichment {
  console.assert(
    typeof payload === "object" && payload !== null,
    "parseEnrichmentPayload: payload must be an object"
  );

  const hours = payload.hours as Record<string, unknown> | undefined;
  const weekdayText = hours?.weekday_text;
  const rawPeriods = hours?.periods;

  const parsedPeriods = parsePeriods(rawPeriods);

  const enrichment: StoreEnrichment = {
    hours_weekday_text: Array.isArray(weekdayText)
      ? (weekdayText as string[])
      : null,
    hours_periods: parsedPeriods,
    rating: typeof payload.rating === "number" ? payload.rating : null,
    user_rating_count:
      typeof payload.user_rating_count === "number"
        ? payload.user_rating_count
        : null,
    photo_refs: Array.isArray(payload.photo_refs)
      ? (payload.photo_refs as string[])
      : null,
    enriched_at:
      typeof payload.enriched_at === "string" ? payload.enriched_at : null,
  };

  console.assert(
    enrichment.rating === null ||
      (enrichment.rating >= 0 && enrichment.rating <= 5),
    "parseEnrichmentPayload: rating must be between 0 and 5 or null"
  );

  return enrichment;
}

export async function getStoreEnrichment(
  storeId: string
): Promise<StoreEnrichment | null> {
  console.assert(
    typeof storeId === "string" && storeId.length > 0,
    "getStoreEnrichment: storeId must be a non-empty string"
  );

  try {
    const rows = await query<{ payload: Record<string, unknown> }>(
      `SELECT payload FROM store_external_refs
       WHERE store_id = $1 AND provider = 'google_places'
       LIMIT 1`,
      [storeId]
    );

    console.assert(
      Array.isArray(rows),
      "getStoreEnrichment: rows must be an array"
    );

    if (rows.length === 0 || rows[0].payload === null) {
      return null;
    }

    return parseEnrichmentPayload(rows[0].payload);
  } catch {
    // Table may not have data yet -- degrade gracefully
    return null;
  }
}

export async function getStoreEnrichments(
  storeIds: string[]
): Promise<Map<string, StoreEnrichment>> {
  console.assert(
    Array.isArray(storeIds),
    "getStoreEnrichments: storeIds must be an array"
  );
  console.assert(
    storeIds.length >= 0,
    "getStoreEnrichments: storeIds length must be non-negative"
  );

  const enrichmentMap = new Map<string, StoreEnrichment>();

  if (storeIds.length === 0) {
    return enrichmentMap;
  }

  try {
    const rows = await query<{
      store_id: string;
      payload: Record<string, unknown>;
    }>(
      `SELECT store_id, payload FROM store_external_refs
       WHERE store_id = ANY($1) AND provider = 'google_places'`,
      [storeIds]
    );

    console.assert(
      Array.isArray(rows),
      "getStoreEnrichments: rows must be an array"
    );

    const rowLimit = Math.min(rows.length, 10_000);
    for (let i = 0; i < rowLimit; i++) {
      const row = rows[i];
      if (row.payload !== null) {
        enrichmentMap.set(row.store_id, parseEnrichmentPayload(row.payload));
      }
    }

    return enrichmentMap;
  } catch {
    // Table may not have data yet -- degrade gracefully
    return enrichmentMap;
  }
}

function parseContentPayload(
  payload: Record<string, unknown>
): StoreContent {
  console.assert(
    typeof payload === "object" && payload !== null,
    "parseContentPayload: payload must be an object"
  );

  const products = Array.isArray(payload.products)
    ? (payload.products as string[])
    : [];

  const content: StoreContent = {
    description:
      typeof payload.description === "string" ? payload.description : null,
    products,
    has_events: payload.has_events === true,
    event_url:
      typeof payload.event_url === "string" ? payload.event_url : null,
  };

  console.assert(
    Array.isArray(content.products),
    "parseContentPayload: products must be an array"
  );

  return content;
}

export async function getStoreContent(
  storeId: string
): Promise<StoreContent | null> {
  console.assert(
    typeof storeId === "string" && storeId.length > 0,
    "getStoreContent: storeId must be a non-empty string"
  );

  try {
    const rows = await query<{ payload: Record<string, unknown> }>(
      `SELECT payload FROM store_external_refs
       WHERE store_id = $1 AND provider = 'website_content'
       LIMIT 1`,
      [storeId]
    );

    console.assert(
      Array.isArray(rows),
      "getStoreContent: rows must be an array"
    );

    if (rows.length === 0 || rows[0].payload === null) {
      return null;
    }

    return parseContentPayload(rows[0].payload);
  } catch {
    // Table may not have data yet -- degrade gracefully
    return null;
  }
}

export async function getStoreContents(
  storeIds: string[]
): Promise<Map<string, StoreContent>> {
  console.assert(
    Array.isArray(storeIds),
    "getStoreContents: storeIds must be an array"
  );
  console.assert(
    storeIds.length >= 0,
    "getStoreContents: storeIds length must be non-negative"
  );

  const contentMap = new Map<string, StoreContent>();

  if (storeIds.length === 0) {
    return contentMap;
  }

  try {
    const rows = await query<{
      store_id: string;
      payload: Record<string, unknown>;
    }>(
      `SELECT store_id, payload FROM store_external_refs
       WHERE store_id = ANY($1) AND provider = 'website_content'`,
      [storeIds]
    );

    console.assert(
      Array.isArray(rows),
      "getStoreContents: rows must be an array"
    );

    const rowLimit = Math.min(rows.length, 10_000);
    for (let i = 0; i < rowLimit; i++) {
      const row = rows[i];
      if (row.payload !== null) {
        contentMap.set(row.store_id, parseContentPayload(row.payload));
      }
    }

    return contentMap;
  } catch {
    // Table may not have data yet -- degrade gracefully
    return contentMap;
  }
}

export async function getStoreCategories(
  storeId: string
): Promise<StoreCategory[]> {
  console.assert(
    typeof storeId === "string" && storeId.length > 0,
    "getStoreCategories: storeId must be a non-empty string"
  );

  const rows = await query<{ category: string }>(
    `SELECT category FROM store_categories WHERE store_id = $1`,
    [storeId]
  );

  console.assert(Array.isArray(rows), "getStoreCategories: rows must be an array");
  return rows.map((r) => r.category as StoreCategory);
}

interface ListStoresByCategoryResult {
  stores: Store[];
  total: number;
  page: number;
  pageSize: number;
}

export async function listStoresByCategory(
  category: string,
  params: { page?: number; state?: string; city?: string }
): Promise<ListStoresByCategoryResult> {
  console.assert(
    typeof category === "string" && category.length > 0,
    "listStoresByCategory: category must be a non-empty string"
  );

  const page = params.page ?? 1;
  console.assert(page >= 1, "listStoresByCategory: page must be >= 1");
  const offset = (page - 1) * PAGE_SIZE;

  const conditions: string[] = [
    `status IN ('active', 'verified', 'candidate')`,
    `id IN (SELECT store_id FROM store_categories WHERE category = $1)`,
  ];
  const values: unknown[] = [category];
  let idx = 2;

  if (params.state) {
    conditions.push(`address->>'state' = $${idx++}`);
    values.push(params.state.toUpperCase());
  }
  if (params.city) {
    conditions.push(`UPPER(address->>'city') = UPPER($${idx++})`);
    values.push(params.city);
  }

  const where = `WHERE ${conditions.join(" AND ")}`;

  const countRows = await query<{ total: number }>(
    `SELECT count(*)::int as total FROM stores ${where} ${TRUSTED_CANDIDATE_FILTER}`,
    values
  );
  const total = countRows[0]?.total ?? 0;

  const stores = await query<Store>(
    `SELECT * FROM stores ${where} ${TRUSTED_CANDIDATE_FILTER}
     ORDER BY name ASC
     LIMIT $${idx++} OFFSET $${idx++}`,
    [...values, PAGE_SIZE, offset]
  );

  return { stores, total, page, pageSize: PAGE_SIZE };
}

export async function getCategoryStats(): Promise<
  { category: string; count: number }[]
> {
  const rows = await query<{ category: string; count: number }>(
    `SELECT category, count(*)::int as count
     FROM store_categories
     GROUP BY category
     ORDER BY count DESC`
  );

  console.assert(Array.isArray(rows), "getCategoryStats: rows must be an array");
  return rows;
}

export async function getTotalStoreCount(): Promise<number> {
  const rows = await query<{ total: number }>(
    `SELECT count(*)::int as total FROM stores
     WHERE status IN ('active', 'verified', 'candidate')
     ${TRUSTED_CANDIDATE_FILTER}`
  );

  console.assert(Array.isArray(rows), "getTotalStoreCount: rows must be an array");
  console.assert(rows.length === 1, "getTotalStoreCount: expected exactly one row");
  return rows[0]?.total ?? 0;
}

export async function getPopularCities(
  limit: number = 12
): Promise<{ city: string; state: string; store_count: number }[]> {
  console.assert(typeof limit === "number" && limit > 0, "getPopularCities: limit must be positive");
  console.assert(limit <= 100, "getPopularCities: limit must be <= 100");

  const rows = await query<{ city: string; state: string; store_count: number }>(
    `SELECT
       address->>'city' AS city,
       address->>'state' AS state,
       COUNT(*)::int AS store_count
     FROM stores
     WHERE status IN ('active', 'verified', 'candidate')
       ${TRUSTED_CANDIDATE_FILTER}
       AND address->>'city' IS NOT NULL
       AND address->>'state' IS NOT NULL
     GROUP BY address->>'city', address->>'state'
     ORDER BY store_count DESC
     LIMIT $1`,
    [limit]
  );

  console.assert(Array.isArray(rows), "getPopularCities: rows must be an array");
  return rows;
}

/**
 * Returns the top (state, city) slug pairs by store count, intended for
 * build-time prerender (`generateStaticParams`) of `/stores/[state]/[city]`.
 *
 * Separate from `getPopularCities` so UI callers keep their 100-cap
 * contract while the prerender path can request a larger set (up to 500)
 * to bound build time while still covering long-tail traffic. Per Rex B1.
 */
export async function getTopCityStateSlugs(
  limit: number
): Promise<{ city: string; state: string }[]> {
  console.assert(typeof limit === "number" && limit > 0, "getTopCityStateSlugs: limit must be positive");
  console.assert(limit <= 500, "getTopCityStateSlugs: limit must be <= 500 (prerender bound)");

  const rows = await query<{ city: string; state: string }>(
    `SELECT
       address->>'city' AS city,
       address->>'state' AS state
     FROM stores
     WHERE status IN ('active', 'verified', 'candidate')
       ${TRUSTED_CANDIDATE_FILTER}
       AND address->>'city' IS NOT NULL
       AND address->>'state' IS NOT NULL
     GROUP BY address->>'city', address->>'state'
     ORDER BY COUNT(*) DESC
     LIMIT $1`,
    [limit]
  );

  console.assert(Array.isArray(rows), "getTopCityStateSlugs: rows must be an array");
  return rows;
}

/**
 * Returns other stores in the same city, excluding the given store.
 * Used for "Other Stores in [City]" section on store detail pages.
 */
export async function getOtherStoresInCity(
  storeId: string,
  state: string,
  city: string,
  limit: number = 6
): Promise<Store[]> {
  console.assert(typeof storeId === "string" && storeId.length > 0, "getOtherStoresInCity: storeId must be non-empty");
  console.assert(typeof state === "string" && state.length > 0, "getOtherStoresInCity: state must be non-empty");
  console.assert(typeof city === "string" && city.length > 0, "getOtherStoresInCity: city must be non-empty");
  console.assert(limit > 0 && limit <= 50, "getOtherStoresInCity: limit must be 1-50");

  const rows = await query<Store>(
    `SELECT * FROM stores
     WHERE UPPER(address->>'state') = UPPER($1)
       AND UPPER(address->>'city') = UPPER($2)
       AND id != $3
       AND status IN ('active', 'verified', 'candidate')
       ${TRUSTED_CANDIDATE_FILTER}
     ORDER BY name ASC
     LIMIT $4`,
    [state, city, storeId, limit]
  );

  console.assert(Array.isArray(rows), "getOtherStoresInCity: rows must be an array");
  return rows;
}

/**
 * Returns the top cities by store count for a given category.
 * Used for internal linking on category pages.
 */
export async function getTopCitiesForCategory(
  category: string,
  limit: number = 10
): Promise<{ city: string; state: string; store_count: number }[]> {
  console.assert(typeof category === "string" && category.length > 0, "getTopCitiesForCategory: category must be non-empty");
  console.assert(limit > 0 && limit <= 50, "getTopCitiesForCategory: limit must be 1-50");

  const rows = await query<{ city: string; state: string; store_count: number }>(
    `SELECT
       s.address->>'city' AS city,
       s.address->>'state' AS state,
       COUNT(*)::int AS store_count
     FROM stores s
     INNER JOIN store_categories sc ON sc.store_id = s.id
     WHERE sc.category = $1
       AND s.status IN ('active', 'verified', 'candidate')
       AND NOT (
         s.status = 'candidate'
         AND s.wpn_id IS NULL
         AND s.id NOT IN (
           SELECT store_id FROM store_external_refs
           WHERE provider = 'website_content'
             AND jsonb_array_length(COALESCE(payload->'products', '[]'::jsonb)) > 0
         )
       )
       AND s.address->>'city' IS NOT NULL
       AND s.address->>'state' IS NOT NULL
     GROUP BY s.address->>'city', s.address->>'state'
     ORDER BY store_count DESC
     LIMIT $2`,
    [category, limit]
  );

  console.assert(Array.isArray(rows), "getTopCitiesForCategory: rows must be an array");
  return rows;
}

/** Product/game tag counts across all stores with website content data */
export async function getGameTagCounts(): Promise<
  { tag: string; count: number }[]
> {
  try {
    const rows = await query<{ tag: string; count: number }>(
      `SELECT
         elem AS tag,
         COUNT(DISTINCT store_id)::int AS count
       FROM store_external_refs,
         LATERAL jsonb_array_elements_text(payload->'products') AS elem
       WHERE provider = 'website_content'
       GROUP BY elem
       ORDER BY count DESC`
    );

    console.assert(Array.isArray(rows), "getGameTagCounts: rows must be an array");
    return rows;
  } catch (err) {
    console.error("getGameTagCounts: query failed", err);
    return [];
  }
}
