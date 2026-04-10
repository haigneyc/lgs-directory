# Roll For Store — SEO Architecture Decisions

## Slug Strategy

Stores are addressed by slug (`/store/[slug]`) not UUID (`/store/[uuid]`).

- Slugs are generated at ingest time from store name + city
- Old UUID-based URLs return 308 permanent redirects to the slug URL
- 308 (not 301) is used to preserve query strings on redirect
- A small number of stores (13 as of 2026-04-08) had null slugs — these were backfilled; the pipeline ingest path that was bypassing slug generation was fixed

**Never** change a store's slug once it has been indexed — it resets search rankings for that URL.

## Trust Filter

Candidate stores are not shown in the public directory unless they pass trust signals (WPN, content scraper, or Games Workshop). This prevents junk candidates from being indexed.

See `lib/queries.ts` `TRUSTED_CANDIDATE_FILTER` for implementation.

## Soft-404 Handling

When a store slug doesn't exist in the database, call `notFound()` from `next/navigation`. This triggers the Next.js 404 page (HTTP 404) rather than rendering an empty page with HTTP 200.

Never return a 200 response for a non-existent store — Google will soft-404-penalize pages that look empty.

## Per-Store Metadata

Each store detail page generates unique `<title>` and `<meta name="description">` via `lib/store-metadata.ts`. Title format:

```
{Store Name} — {City}, {State} | Roll For Store
```

Title-case the store name (many stores are stored in ALL CAPS from WPN data). The `store-metadata.ts` helper handles this.

## Open Graph Images

Dynamic OG images are generated via `app/opengraph-image.tsx` (root) and per-route variants. Each uses `ImageResponse` from `next/og`.

## JSON-LD Structured Data

Store detail pages include `LocalBusiness` JSON-LD schema. Key fields:
- `@type`: `LocalBusiness` (or `GameStore` if available in schema.org)
- `name`, `address`, `telephone`, `url`, `openingHoursSpecification`
- `geo` with latitude/longitude

Do not add JSON-LD to list pages — it adds noise without value.

## Sitemap

`app/sitemap.ts` generates the XML sitemap. It queries all active stores and state/city directory pages. Regenerated at build time.

Sitemap does not include candidate stores (only `status = 'active'` or equivalent).

## State and City Pages

- `/stores/[state]` — indexed by state slug (e.g., `/stores/texas`)
- `/stores/[state]/[city]` — indexed by state + city slug

State slugs use full state name lowercase (not abbreviation): `texas`, `new-york`, etc. Helpers in `lib/slugs.ts`.

## Robots

`app/robots.ts` allows all crawlers by default. No paths are disallowed except `/api/`.

## Known SEO Issues / History

- UUID→slug 308 redirect: shipped on `seo/uuid-308-redirect` branch
- Per-store meta descriptions: shipped on `rollforstore-per-store-meta-descriptions` branch
- Title-case store names: included in per-store meta branch
- GSC v2 fixes (schema + canonical): `seo/gsc-v2-fixes` branch
- feat/store-expansion merge: dropped the per-store meta changes — always check for this pattern when merging long-lived branches
