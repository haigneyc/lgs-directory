const LLMS_CONTENT = `# Roll For Store
> A comprehensive directory of local game stores in the United States.

## What this site contains
- 5,500+ local game stores across all 50 US states
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

export function GET(): Response {
  console.assert(typeof LLMS_CONTENT === "string", "GET: LLMS_CONTENT must be a string");
  console.assert(LLMS_CONTENT.length > 0, "GET: LLMS_CONTENT must not be empty");

  return new Response(LLMS_CONTENT, {
    status: 200,
    headers: {
      "Content-Type": "text/plain",
      "Cache-Control": "public, max-age=86400",
    },
  });
}
