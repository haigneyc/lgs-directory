# Slug Backfill — 13 Null-Slug Stores

**Status:** active
**Priority:** P3 (sitemap correctness)
**Owner:** Soren

## Context

As of 2026-04-08, 13 of 6,117 `stores` rows have `slug IS NULL`. The sitemap at `web/app/sitemap.ts` falls back to `/store/${row.id}` (UUID) for these, which defeats the slug migration for those specific stores. Known offenders include Cardboard Collectibles (Council Bluffs IA), From The Ashes Games (Trenton MO), Golem Trading (Grand Junction IA), High Roll Games (Iowa Falls IA), Hidden Vault Games (Rogers AR).

## Acceptance criteria

- [ ] Verify current null-slug count: `SELECT COUNT(*) FROM stores WHERE slug IS NULL;` against Neon prod DB
- [ ] Run one-time backfill: generate slugs via the same helper the trigger uses, `UPDATE stores SET slug = ... WHERE slug IS NULL`
- [ ] Identify which pipeline path is bypassing slug generation on insert (eBay import? Google Places seed? Manual admin insert?)
- [ ] Add slug generation to any pipeline paths that are missing it so the count stays at 0 going forward
- [ ] Verify sitemap contains zero UUID-style URLs for previously null-slug stores

## Notes

- Verify count before acting — may have been fixed in the interim
- Slug generation helper is used by the existing DB trigger; find the equivalent Python function in the pipeline
- Related files: `web/app/sitemap.ts`, Python pipeline store insertion paths
- Rex flagged this on 2026-04-08 from Neon DB inspection
