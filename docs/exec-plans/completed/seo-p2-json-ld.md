# SEO P2 — JSON-LD Structured Data

**Status:** completed
**Priority:** P2
**Shipped:** pre-2026-04-09 (pre-existing)
**Owner:** Soren

## Context

Google needs structured data to understand store entities and produce rich results. LocalBusiness JSON-LD on store detail pages and ItemList JSON-LD on state/city index pages were confirmed present and well-formed before the P1-P3 batch.

## Acceptance criteria

- [x] `LocalBusiness` JSON-LD on `/store/[slug]` pages with absolute `@id`/`url` and `sameAs` from active presences
- [x] `ItemList` JSON-LD on `/stores/[state]` and `/stores/[state]/[city]` pages
- [x] Canonical URLs are absolute

## What shipped

Pre-existing in the codebase. Confirmed during the 2026-04-06 shipment audit. `LocalBusiness` enrichment was enhanced on 2026-04-06 with `sameAs` from `store_external_refs`. Minor: `web/app/stores/page.tsx:93` uses `sorted.length` for `numberOfItems` instead of `itemListElements.length` — Rex flagged as cosmetic (practically impossible to diverge).
