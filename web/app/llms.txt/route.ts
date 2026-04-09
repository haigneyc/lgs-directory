import { cacheLife } from "next/cache";
import { getTotalStoreCount } from "@/lib/queries";

/**
 * Round a live store count down to the nearest 100 so the published
 * llms.txt copy ages gracefully between data refreshes. Petra QA
 * (2026-04-08) caught the static "5,500+" string while the sitemap had
 * 6,117 real URLs — making this dynamic prevents that drift.
 */
function roundDownToHundred(count: number): number {
  console.assert(Number.isFinite(count), "roundDownToHundred: count must be finite");
  console.assert(count >= 0, "roundDownToHundred: count must be non-negative");
  return Math.floor(count / 100) * 100;
}

async function buildLlmsBody(): Promise<string> {
  "use cache";
  // Cache Components-compatible cache directive. The store count only
  // changes a few times a day via the seeder, so a per-request DB hit
  // here is pure waste (Rex concern 7, 2026-04-08). The cache
  // directive must wrap a plain-value return (string), not a
  // `Response` — `Response` is not a serialisable cache payload.
  cacheLife("hours");
  const storeCount = await getTotalStoreCount();
  console.assert(Number.isInteger(storeCount), "buildLlmsBody: storeCount must be an integer");
  console.assert(storeCount >= 0, "buildLlmsBody: storeCount must be non-negative");
  return buildLlmsContent(storeCount);
}

function buildLlmsContent(storeCount: number): string {
  console.assert(Number.isInteger(storeCount), "buildLlmsContent: storeCount must be an integer");
  console.assert(storeCount >= 0, "buildLlmsContent: storeCount must be non-negative");
  const rounded = roundDownToHundred(storeCount);
  return `# Roll For Store
> A comprehensive directory of local game stores in the United States.

## What this site contains
- ${rounded.toLocaleString()}+ local game stores across all 50 US states
- Store details: name, address, phone, WPN authorization status
- Online presence: website URLs, e-commerce platforms, MTG singles availability
- Location data: latitude/longitude coordinates for mapping

## How to use this data
- Browse by state: /stores/{state-name}
- Browse by city: /stores/{state-name}/{city-name}
- Individual store: /store/{store-slug}  (legacy /store/{store-uuid} URLs 301-redirect to the slug form)
- Sitemap: /sitemap.xml

## Data freshness
- Store data validated every 12 hours via automated pipeline
- Sources: WPN Store Locator, Google Places API
`;
}

export async function GET(): Promise<Response> {
  const body = await buildLlmsBody();
  console.assert(body.length > 0, "GET: body must not be empty");

  return new Response(body, {
    status: 200,
    headers: {
      "Content-Type": "text/plain",
      "Cache-Control": "public, max-age=86400",
    },
  });
}
