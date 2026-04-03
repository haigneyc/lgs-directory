#!/usr/bin/env bun
/**
 * generate-city-descriptions.ts
 *
 * Standalone Bun script that generates AI city descriptions for SEO pages.
 * Uses data from the DB (store count, names, WPN levels, online presence)
 * and calls the Anthropic Claude API to produce 2-3 sentence descriptions.
 *
 * Usage (run from web/ directory so Bun resolves node_modules):
 *   cd web && DATABASE_URL=... ANTHROPIC_API_KEY=... bun run ../scripts/generate-city-descriptions.ts
 *
 * Safe to re-run — upserts on (state, city) unique constraint.
 */

import Anthropic from "@anthropic-ai/sdk";
import { Pool } from "@neondatabase/serverless";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const MODEL = "claude-haiku-4-5-20251001";
const RATE_LIMIT_MS = 1000; // 1 request per second
const MIN_STORES_PER_CITY = 2;
const MAX_CITIES = 10_000; // upper bound for loop safety
const MAX_STORES_PER_CITY_CONTEXT = 20; // cap store names sent to the prompt

// ---------------------------------------------------------------------------
// DB helpers
// ---------------------------------------------------------------------------

function createPool(): Pool {
  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) {
    throw new Error("DATABASE_URL environment variable is not set");
  }
  return new Pool({ connectionString });
}

interface CityRow {
  state: string;
  city: string;
  store_count: number;
  active_count: number;
  wpn_premium_count: number;
  online_count: number;
}

interface StoreContextRow {
  name: string;
  wpn_level: string | null;
  has_online: boolean;
  sells_singles: boolean;
}

async function fetchCities(pool: Pool): Promise<CityRow[]> {
  const result = await pool.query<CityRow>(
    `SELECT
       address->>'state' AS state,
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
       AND address->>'state' IS NOT NULL
       AND address->>'city' IS NOT NULL
     GROUP BY address->>'state', address->>'city'
     HAVING COUNT(*) >= $1
     ORDER BY address->>'state', address->>'city'`,
    [MIN_STORES_PER_CITY]
  );

  console.assert(Array.isArray(result.rows), "fetchCities: rows must be an array");
  console.assert(result.rows.length >= 0, "fetchCities: rows length must be non-negative");

  return result.rows;
}

async function fetchStoreContext(
  pool: Pool,
  state: string,
  city: string
): Promise<StoreContextRow[]> {
  console.assert(typeof state === "string" && state.length > 0, "fetchStoreContext: state required");
  console.assert(typeof city === "string" && city.length > 0, "fetchStoreContext: city required");

  const result = await pool.query<StoreContextRow>(
    `SELECT
       s.name,
       s.wpn_level,
       EXISTS (
         SELECT 1 FROM online_presences op
         WHERE op.store_id = s.id AND op.status = 'active'
       ) AS has_online,
       EXISTS (
         SELECT 1 FROM online_presences op
         WHERE op.store_id = s.id AND op.sells_mtg_singles = true AND op.status = 'active'
       ) AS sells_singles
     FROM stores s
     WHERE UPPER(s.address->>'state') = UPPER($1)
       AND UPPER(s.address->>'city') = UPPER($2)
       AND s.status IN ('active', 'verified', 'candidate')
     ORDER BY s.name
     LIMIT $3`,
    [state, city, MAX_STORES_PER_CITY_CONTEXT]
  );

  console.assert(Array.isArray(result.rows), "fetchStoreContext: rows must be an array");

  return result.rows;
}

async function upsertDescription(
  pool: Pool,
  state: string,
  city: string,
  description: string,
  model: string
): Promise<void> {
  console.assert(typeof state === "string" && state.length > 0, "upsertDescription: state required");
  console.assert(typeof city === "string" && city.length > 0, "upsertDescription: city required");
  console.assert(typeof description === "string" && description.length > 0, "upsertDescription: description required");
  console.assert(typeof model === "string" && model.length > 0, "upsertDescription: model required");

  await pool.query(
    `INSERT INTO city_descriptions (state, city, description, model, generated_at)
     VALUES ($1, $2, $3, $4, NOW())
     ON CONFLICT (state, city)
     DO UPDATE SET description = $3, model = $4, generated_at = NOW()`,
    [state, city, description, model]
  );
}

// ---------------------------------------------------------------------------
// Prompt builder
// ---------------------------------------------------------------------------

function buildPrompt(cityRow: CityRow, stores: StoreContextRow[]): string {
  console.assert(stores.length > 0, "buildPrompt: must have at least one store");

  const storeNames = stores.map((s) => s.name);
  const wpnStores = stores.filter((s) => s.wpn_level !== null);
  const wpnPremiumStores = stores.filter((s) => s.wpn_level === "premium");
  const onlineStores = stores.filter((s) => s.has_online);
  const singlesStores = stores.filter((s) => s.sells_singles);

  const contextLines: string[] = [
    `City: ${cityRow.city}, ${cityRow.state}`,
    `Total game stores: ${cityRow.store_count}`,
    `Active/verified stores: ${cityRow.active_count}`,
    `Store names: ${storeNames.join(", ")}`,
  ];

  if (wpnStores.length > 0) {
    contextLines.push(
      `WPN-authorized stores: ${wpnStores.length} (${wpnStores.map((s) => s.name).join(", ")})`
    );
  }
  if (wpnPremiumStores.length > 0) {
    contextLines.push(
      `WPN Premium stores: ${wpnPremiumStores.length} (${wpnPremiumStores.map((s) => s.name).join(", ")})`
    );
  }
  if (onlineStores.length > 0) {
    contextLines.push(`Stores with online presence: ${onlineStores.length}`);
  }
  if (singlesStores.length > 0) {
    contextLines.push(`Stores selling MTG singles online: ${singlesStores.length}`);
  }

  return contextLines.join("\n");
}

const SYSTEM_PROMPT = `You write brief, factual descriptions of cities' tabletop gaming scenes for a game store directory website. Your descriptions are used on SEO city pages.

Rules:
- Write exactly 2-3 sentences.
- Be factual and grounded in the provided data. Do not invent details.
- Mention the city name, approximate store count, and any notable details (WPN status, online sellers).
- Use a neutral, informative tone — not marketing fluff.
- Do not use superlatives like "best" or "top" unless the data supports it.
- Do not start with "Welcome to" or similar greetings.
- Output ONLY the description text, nothing else.`;

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main(): Promise<void> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error("ANTHROPIC_API_KEY environment variable is not set");
  }

  const pool = createPool();
  const client = new Anthropic({ apiKey });

  console.log("Fetching cities with 2+ stores...");
  const cities = await fetchCities(pool);
  console.log(`Found ${cities.length} cities to process.`);

  console.assert(cities.length >= 0, "main: cities count must be non-negative");
  console.assert(cities.length <= MAX_CITIES, "main: cities count exceeds safety limit");

  let processed = 0;
  let errors = 0;
  const cityLimit = Math.min(cities.length, MAX_CITIES);

  for (let i = 0; i < cityLimit; i++) {
    const cityRow = cities[i];
    const label = `${cityRow.city}, ${cityRow.state}`;

    try {
      const stores = await fetchStoreContext(pool, cityRow.state, cityRow.city);
      if (stores.length === 0) {
        console.warn(`  [SKIP] ${label}: no stores found in context query`);
        continue;
      }

      const userPrompt = buildPrompt(cityRow, stores);

      const response = await client.messages.create({
        model: MODEL,
        max_tokens: 256,
        system: SYSTEM_PROMPT,
        messages: [{ role: "user", content: userPrompt }],
      });

      const textBlock = response.content.find((b) => b.type === "text");
      if (!textBlock || textBlock.type !== "text") {
        console.error(`  [ERROR] ${label}: no text in API response`);
        errors++;
        continue;
      }

      const description = textBlock.text.trim();
      if (description.length === 0) {
        console.error(`  [ERROR] ${label}: empty description from API`);
        errors++;
        continue;
      }

      await upsertDescription(pool, cityRow.state, cityRow.city, description, MODEL);
      processed++;

      console.log(`  [${processed}/${cities.length}] ${label} — ${description.length} chars`);

      // Rate limit: wait before next API call
      if (i < cityLimit - 1) {
        await sleep(RATE_LIMIT_MS);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      console.error(`  [ERROR] ${label}: ${message}`);
      errors++;
    }
  }

  console.log(`\nDone. Processed: ${processed}, Errors: ${errors}, Total cities: ${cities.length}`);

  await pool.end();
}

main().catch((err: unknown) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
