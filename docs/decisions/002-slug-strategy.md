# ADR-002: Slug Strategy

**Date:** 2026-04-09
**Status:** accepted

## Context

Store detail pages were originally served at `/store/[uuid]` (UUID from the database primary key). UUID URLs are opaque, carry no semantic value for SEO, and cannot transfer ranking signal when a store record is replaced or merged. A migration to human-readable slug URLs was needed.

## Decision

Stores are addressed by slug (`/store/[slug]`) generated from store name + city at ingest time. The slug generation helper normalizes to lowercase, strips punctuation, and deduplicates collisions with a numeric suffix.

UUID-to-slug redirects are **308 Permanent Redirect** (not 301). 308 was chosen over 301 to preserve query strings on redirect.

**Redirect implementation: middleware (proxy.ts), not Next.js `redirects` config.** This was a hard-won lesson: a 308 thrown from inside a Server Component nested in a `<Suspense>` boundary arrives too late — the streaming shell has already been sent with HTTP 200 before the redirect can take effect. Moving the redirect to `proxy.ts` (Next.js middleware) ensures it runs before any rendering begins, so Googlebot and CDNs see the correct 308 status. See ADR-007 for the full incident post-mortem.

**Slug immutability:** Once a store slug has been indexed by Google, it must not change. Changing a slug resets search rankings for that URL. If a store is renamed or merged, create a new slug and add a 308 from the old slug in proxy.ts — do not update the slug column in place.

**Null slug gap:** As of 2026-04-08, 13 of 6,117 stores had null slugs — these were inserted via a pipeline path that bypassed slug generation. A one-time backfill was completed. The sitemap falls back to `/store/${uuid}` for any future null-slug rows, which is a detectable regression to watch for. Verify periodically with `SELECT COUNT(*) FROM stores WHERE slug IS NULL`.

## Consequences

- 6,104 stores backfilled with slugs on 2026-04-06.
- UUID URLs return 308 to slug URL in proxy.ts — Googlebot sees correct permanent redirect.
- `loadSlugCache()` in proxy.ts maintains an in-memory Set of known slugs with 5-min TTL for fast redirect lookups.
- Pipeline ingest paths must always populate slug — no exceptions.

## Notes

- See `web/lib/proxy.ts` for redirect implementation.
- See also `docs/seo-decisions.md` — Slug Strategy section (covers same ground, this ADR adds the proxy.ts decision rationale).
- See ADR-007 for the full post-mortem on why Suspense-nested redirects fail.
- P6 open item: `loadSlugCache()` should have a `LIMIT 100000` sanity cap on its SELECT query.
