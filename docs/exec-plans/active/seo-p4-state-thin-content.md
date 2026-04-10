# SEO P4 — State Page Thin-Content Fixes

**Status:** active
**Priority:** P4
**Owner:** Petra (diagnostic) then Soren (fix)

## Context

Three state pages are ranking poorly, likely due to thin content or weak internal linking: `/stores/colorado` (pos 54.73), `/stores/oregon` (54.71), `/stores/south-carolina` (44.59). This is the next SEO lever after P1-P3 shipped on 2026-04-09.

## Acceptance criteria

- [ ] Petra runs diagnostic: identify root cause (thin content vs. poor internal linking vs. crawl budget issue)
- [ ] Soren implements fix based on Petra's recommendation
- [ ] Affected state pages show richer content or improved internal linking structure
- [ ] Pages re-submitted for indexing via GSC after fix

## Notes

- P1-P3 (per-store metadata, JSON-LD, /near-me, /stores index, favicon) shipped 2026-04-09
- Petra should check: store count per state, quality of state-level description/heading, internal links from homepage to state pages, and whether ItemList JSON-LD is well-formed
- Related files: `web/app/stores/[state]/page.tsx`, `web/lib/queries.ts`
