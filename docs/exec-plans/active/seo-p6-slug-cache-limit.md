# SEO P6 — loadSlugCache LIMIT Defense

**Status:** active
**Priority:** P6
**Owner:** Soren

## Context

`loadSlugCache()` in `web/lib/proxy.ts` runs `SELECT slug FROM stores WHERE slug IS NOT NULL` with no row cap. At 6,117 stores this is fine, but as the directory grows this becomes a memory risk on cold start. A `LIMIT 100000` sanity cap prevents runaway memory usage without breaking anything at current scale.

## Acceptance criteria

- [ ] Add `LIMIT 100000` to the slug SELECT query in `loadSlugCache()`
- [ ] Add a runtime assertion that the returned set size is > 0 (non-empty cache is a health signal)
- [ ] Verify `tsc --noEmit` and `bun run lint` pass with zero warnings

## Notes

- Non-urgent — current count is ~6,100 slugs, well under any realistic limit
- Revisit if/when the directory exceeds 50k stores
- Related file: `web/lib/proxy.ts`
