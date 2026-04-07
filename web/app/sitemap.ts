import type { MetadataRoute } from "next";
import { query } from "@/lib/db";
import { SITE_URL } from "@/lib/site";
import { stateToSlug, cityToSlug } from "@/lib/slugs";

const BASE_URL = SITE_URL;
const MAX_SITEMAP_ENTRIES = 50000;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  console.assert(typeof BASE_URL === "string", "sitemap: BASE_URL must be a string");
  console.assert(MAX_SITEMAP_ENTRIES > 0, "sitemap: MAX_SITEMAP_ENTRIES must be positive");

  const entries: MetadataRoute.Sitemap = [];

  // 1. Homepage
  entries.push({
    url: BASE_URL,
    priority: 1.0,
    changeFrequency: "weekly",
  });

  // 2. Affiliate disclosure (static legal page).
  entries.push({
    url: `${BASE_URL}/affiliate-disclosure`,
    priority: 0.3,
    changeFrequency: "yearly",
  });

  // 3. Category pages (comics, retro-games, warhammer)
  const categoryPaths = ["/comics", "/retro-games", "/warhammer"];
  console.assert(Array.isArray(categoryPaths), "sitemap: categoryPaths must be an array");

  for (let i = 0; i < categoryPaths.length; i++) {
    entries.push({
      url: `${BASE_URL}${categoryPaths[i]}`,
      priority: 0.9,
      changeFrequency: "weekly",
    });
  }

  // 3. State pages
  const stateRows = await query<{ state: string }>(
    `SELECT DISTINCT address->>'state' AS state
     FROM stores
     WHERE address->>'state' IS NOT NULL
     ORDER BY state`
  );

  console.assert(Array.isArray(stateRows), "sitemap: stateRows must be an array");

  const stateLimit = Math.min(stateRows.length, MAX_SITEMAP_ENTRIES - entries.length);
  for (let i = 0; i < stateLimit; i++) {
    const row = stateRows[i];
    console.assert(typeof row.state === "string", "sitemap: state must be a string");
    entries.push({
      url: `${BASE_URL}/stores/${stateToSlug(row.state)}`,
      priority: 0.8,
      changeFrequency: "weekly",
    });
  }

  // 4. City pages (2+ stores)
  const cityRows = await query<{ state: string; city: string }>(
    `SELECT address->>'state' AS state, address->>'city' AS city
     FROM stores
     WHERE address->>'state' IS NOT NULL
       AND address->>'city' IS NOT NULL
     GROUP BY address->>'state', address->>'city'
     HAVING COUNT(*) >= 2
     ORDER BY state, city`
  );

  console.assert(Array.isArray(cityRows), "sitemap: cityRows must be an array");

  const cityLimit = Math.min(cityRows.length, MAX_SITEMAP_ENTRIES - entries.length);
  for (let i = 0; i < cityLimit; i++) {
    const row = cityRows[i];
    console.assert(typeof row.state === "string", "sitemap: city row state must be a string");
    console.assert(typeof row.city === "string", "sitemap: city must be a string");
    entries.push({
      url: `${BASE_URL}/stores/${stateToSlug(row.state)}/${cityToSlug(row.city)}`,
      priority: 0.6,
      changeFrequency: "weekly",
    });
  }

  // 5. Store detail pages
  const storeRows = await query<{ id: string }>(
    `SELECT id FROM stores ORDER BY id`
  );

  console.assert(Array.isArray(storeRows), "sitemap: storeRows must be an array");

  const storeLimit = Math.min(storeRows.length, MAX_SITEMAP_ENTRIES - entries.length);
  for (let i = 0; i < storeLimit; i++) {
    const row = storeRows[i];
    console.assert(typeof row.id === "string", "sitemap: store id must be a string");
    entries.push({
      url: `${BASE_URL}/store/${row.id}`,
      priority: 0.4,
      changeFrequency: "monthly",
    });
  }

  return entries;
}
