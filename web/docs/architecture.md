# Roll For Store — Web Architecture

## Stack

| Layer | Tech |
|-------|------|
| Framework | Next.js 16 (App Router), React 19, TypeScript |
| Styling | Tailwind CSS v4, shadcn/ui (Base UI + Radix primitives) |
| Database client | `@neondatabase/serverless` (pg-compatible) |
| Cache | Next.js 16 Cache Components (`'use cache'`, `cacheLife`, `cacheTag`) |
| Deployment | Vercel |
| Domain | rollforstore.com |

## Database Connection

Uses `@neondatabase/serverless` Pool. Connects to Supabase via the Supavisor pooler endpoint. Connection string from `DATABASE_URL` env var.

Key constraints (from PERF-027 / Nox A-6):
- Max 3 connections per instance
- 10s idle timeout (prevents socket leaks in serverless)
- Never increase `max` without benchmarking Supavisor limits

## Cache Components Pattern

This app uses Next.js 16 Cache Components (formerly Partial Prerendering / PPR):

- `next.config.ts`: `cacheComponents: true`
- Data functions in `lib/queries.ts` are marked `'use cache'`
- `cacheLife('hours')` / `cacheLife('days')` for TTL
- `cacheTag('stores')`, `cacheTag('stores:state:TX')` for invalidation
- Do NOT use `export const revalidate = ...` in route files — it conflicts with Cache Components

API: `cacheLife` / `cacheTag` are now stable exports from `next/cache` (not `unstable_*`).

## Trust Filter (Candidate Store Visibility)

Candidate stores are hidden from the public site unless they pass at least one of:
1. WPN registration (`wpn_id IS NOT NULL`)
2. Content scraper found game products (`store_external_refs` with `provider = 'website_content'` and non-empty products array)
3. Games Workshop locator hit (`store_external_refs` with `provider = 'games_workshop'`)

This filter lives in `lib/queries.ts` as `TRUSTED_CANDIDATE_FILTER` and is applied to all `listStores` calls. Do not remove it — it prevents low-quality Google Places candidates from polluting the directory.

## URL Structure

| Route | Description |
|-------|-------------|
| `/` | Homepage — all stores, filter bar |
| `/comics` | Comic book stores |
| `/retro-games` | Retro video game stores |
| `/warhammer` | Warhammer & miniatures hobby shops |
| `/stores/[state]` | State directory |
| `/stores/[state]/[city]` | City directory |
| `/store/[slug]` | Store detail page |
| `/near-me` | Geolocation-based search |
| `/affiliate-disclosure` | Affiliate disclosure page |

Category routes are driven by `lib/category-routes.ts` (`CATEGORY_ROUTES` array). Add new categories there first; they automatically populate nav, pages, and metadata.

## Store Categories (Database Values)

| DB value | URL slug | Label |
|----------|----------|-------|
| `comic_shop` | `/comics` | Comic Book Stores |
| `retro_games` | `/retro-games` | Retro Video Game Stores |
| `hobby_miniatures` | `/warhammer` | Warhammer & Hobby Shops |
| (LGS/MTG) | `/` (default) | Local Game Stores |

## Affiliate Integrations

### eBay Ambassador

- Storefront: `https://www.ebay.com/inf/rollforstore`
- Collection URLs for MTG, Pokemon, YGO, F&B, Comics, Warhammer, Board Games
- Defined in `lib/site.ts` as `EBAY_URLS`

### Amazon Associates

- Tag: `orangediscoun-20` (90-day conversion clock, started 2026-04-06)
- Helper in `lib/amazon.ts`

## Key Library Files

| File | Purpose |
|------|---------|
| `lib/queries.ts` | All database query functions (all use `'use cache'`) |
| `lib/db.ts` | `@neondatabase/serverless` pool setup |
| `lib/types.ts` | TypeScript interfaces for Store, OnlinePresence, etc. |
| `lib/slugs.ts` | `stateToSlug`, `cityToSlug` helpers |
| `lib/category-routes.ts` | Category → URL/label/metadata mapping |
| `lib/site.ts` | Site URL, eBay URLs constants |
| `lib/store-metadata.ts` | Per-store `<head>` metadata generation |
| `lib/format.ts` | Display formatting helpers |
| `lib/hours.ts` | Store hours parsing and display |

## SEO Notes

See [docs/seo-decisions.md](seo-decisions.md) for full SEO architecture decisions.

Quick rules:
- Soft-404: missing stores return `notFound()` (triggers Next.js 404 page) — do not return 200 with empty content
- Canonical: always set `alternates.canonical` in page metadata
- Slugs: stores use `/store/[slug]` not `/store/[uuid]` — UUIDs redirect 308 to slug URLs
