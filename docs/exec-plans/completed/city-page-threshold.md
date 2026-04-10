# City Page Threshold — HAVING COUNT >= 1

**Status:** completed
**Shipped:** 2026-04-10
**Owner:** Soren

## Context

City pages were only generated for cities with 2+ stores (`HAVING COUNT >= 2`). Changing this to `HAVING COUNT >= 1` added 2,202 more city pages to the sitemap, each a valid crawlable URL with at least one store result.

## Acceptance criteria

- [x] `getStateIndex()` or city query uses `HAVING COUNT(*) >= 1`
- [x] Sitemap includes the newly unlocked city pages
- [x] No empty city pages (every city page has at least one store)
- [x] City pages with 1 store still render correctly (no layout regressions)

## What shipped

Shipped 2026-04-10. +2,202 city pages added to the sitemap. Each has valid `ItemList` JSON-LD and at least one store card. Improves long-tail indexation coverage significantly.
