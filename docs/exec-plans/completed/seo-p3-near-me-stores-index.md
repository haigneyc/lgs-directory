# SEO P3 — /near-me Rehab + /stores Index + Favicon

**Status:** completed
**Priority:** P3
**Shipped:** 2026-04-09
**Owner:** Soren

## Context

Three small but high-leverage UI/SEO additions that were bundled with P1 in the `feat/lgs-seo-batch-2` branch.

## Acceptance criteria

- [x] `/near-me` — server-rendered via Vercel geo headers (`x-vercel-ip-latitude/longitude/city/country-region`), safe decode wrapper, fallback to US center, client component below as progressive enhancement with prefilled location query
- [x] `/stores` index — new page listing all states via `getStateIndex()` with `ItemList` JSON-LD
- [x] Favicon — `app/icon.tsx` + `app/apple-icon.tsx` (ImageResponse, yellow R monogram on zinc gradient); default `favicon.ico` deleted

## What shipped

All three shipped in `feat/lgs-seo-batch-2` on 2026-04-09 alongside P1. `/stores` index provides a crawlable top-level sitemap for bots. `/near-me` is now SSR instead of client-only, making it indexable and faster for mobile users. Favicon matches the D&D fantasy brand (gold/parchment).
