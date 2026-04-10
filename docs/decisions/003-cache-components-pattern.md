# ADR-003: Cache Components Pattern (PPR Migration)

**Date:** 2026-04-09
**Status:** accepted

## Context

Roll For Store is a Next.js 16 app deployed on Vercel. Before the PERF-027 migration, all pages used `export const revalidate = N` for ISR. Store pages had `revalidate = 86400`, homepage `revalidate = 3600`. Under load, dynamic pages served from cold frequently hit the database.

Next.js 16 ships Cache Components (formerly Partial Prerendering / PPR), which enables fine-grained cache control at the data-function level rather than the page level.

## Decision

Migrate to `cacheComponents: true` in `next.config.ts`. All 22 data query functions in `lib/queries.ts` now use `'use cache'` with `cacheLife`/`cacheTag`. Remove all `export const revalidate` exports from page files (they conflict with Cache Components and cause build failures).

**Key patterns:**

- `cacheLife('hours')` for store listings, city/state pages
- `cacheLife('days')` for relatively static content
- `cacheTag('stores')` for on-demand invalidation when the seeder writes new data
- Page components are **synchronous shell + async `<Suspense>` children** — the shell prerenders statically, async children hydrate from cache. Never `await params` or `await searchParams` at the page level; pass the unresolved Promise to a Suspense-wrapped async child component.

**`/near-me` is NOT cached.** It uses Vercel geo headers (`x-vercel-ip-latitude/longitude`) which are per-request. Caching it would serve one user's geolocation result to another user. The near-me page is marked dynamic and renders server-side on every request.

**PPR → Cache Components rename:** `experimental.ppr = "incremental"` throws in Next 16. Enable only via `cacheComponents: true`. No experimental flag needed.

**API stability:** `cacheLife` and `cacheTag` are stable exports from `next/cache` in Next 16.2+. Do not use `unstable_cacheLife` / `unstable_cacheTag` — they throw runtime errors during prerender.

**Vercel cache verification:** A correctly cached Cache Components response shows both `cache-control: public, max-age=0, must-revalidate` AND `x-vercel-cache: HIT`. The `max-age=0` is correct — it is the browser directive; the edge cache serves from cache. Always test against the canonical `www.` URL (apex redirects don't go through the edge cache and won't show `x-vercel-cache`).

## Consequences

- Petra verified `x-vercel-cache: HIT` on all 7 routes post-migration on 2026-04-06.
- Route table shows pages as `◐ Partial Prerender` (expected).
- Sitemap shows as `ƒ Dynamic` (also expected — dynamic ISR with revalidate).
- Bun emits a benign `setTimeout()` warning at build time — safe to ignore (runs on Node in production).

## Notes

- See `web/next.config.ts` (`cacheComponents: true`), `web/lib/queries.ts` (`'use cache'` functions).
- See also `web/docs/architecture.md` — Cache Components Pattern section (overlaps this ADR; ADR adds the `/near-me` rationale and API gotchas).
- Reference: `/home/chris/.claude/projects/-home-chris-jarvis/memory/reference_next16_cache_components.md`
- LFS (`lfs-locator`) has a pending Cache Components migration (PERF-028) — use this ADR as the implementation guide.
