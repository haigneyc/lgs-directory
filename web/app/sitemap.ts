import type { MetadataRoute } from "next";
import { query } from "@/lib/db";
import { SITE_URL } from "@/lib/site";
import { stateToSlug, cityToSlug } from "@/lib/slugs";
import { getPublishedGuides } from "@/lib/guides";

const BASE_URL = SITE_URL;
const MAX_SITEMAP_ENTRIES = 50000;

export const revalidate = 3600;

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

  // 2a. Guides hub + each published (non-draft) guide post. Driven by
  // the TS registry in ``lib/guides.ts`` so sitemap, index, and route
  // handler all agree on which slugs are live.
  entries.push({
    url: `${BASE_URL}/guides`,
    priority: 0.7,
    changeFrequency: "weekly",
  });

  const guides = getPublishedGuides();
  console.assert(Array.isArray(guides), "sitemap: guides must be an array");
  const guideLimit = Math.min(guides.length, MAX_SITEMAP_ENTRIES - entries.length);
  for (let i = 0; i < guideLimit; i++) {
    const entry = guides[i];
    console.assert(
      typeof entry.meta.slug === "string" && entry.meta.slug.length > 0,
      "sitemap: guide slug must be non-empty",
    );
    entries.push({
      url: `${BASE_URL}/guides/${entry.meta.slug}`,
      lastModified: entry.meta.updatedAt ?? entry.meta.publishedAt,
      priority: 0.7,
      changeFrequency: "monthly",
    });
  }

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

  // 5. Store detail pages -- prefer the human-readable slug URL added
  // for Vera Rec 3. Rows that have not yet been backfilled fall back to
  // the legacy UUID URL, which still resolves (via 301) at the same
  // ``/store/[slug]`` route.
  const storeRows = await query<{ id: string; slug: string | null }>(
    `SELECT id, slug FROM stores ORDER BY id`
  );

  console.assert(Array.isArray(storeRows), "sitemap: storeRows must be an array");

  const storeLimit = Math.min(storeRows.length, MAX_SITEMAP_ENTRIES - entries.length);
  for (let i = 0; i < storeLimit; i++) {
    const row = storeRows[i];
    console.assert(typeof row.id === "string", "sitemap: store id must be a string");
    const path = row.slug !== null && row.slug.length > 0
      ? `/store/${row.slug}`
      : `/store/${row.id}`;
    entries.push({
      url: `${BASE_URL}${path}`,
      priority: 0.4,
      changeFrequency: "monthly",
    });
  }

  return entries;
}
