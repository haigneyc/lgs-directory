# SEO P1 — Per-Store Metadata + Title-Case

**Status:** completed
**Priority:** P1
**Shipped:** 2026-04-09
**Owner:** Soren

## Context

Store names and addresses were displayed in raw all-caps from source data (WPN exports, Google Places). Added a runtime title-case transform and applied it to all metadata, headings, and address display. Also added per-store `<title>` and `<meta description>` tags optimized for SERP snippets.

## Acceptance criteria

- [x] `web/lib/display-case.ts` — runtime transform: all-caps only, acronym allowlist (MTG/TCG/D&D/etc.), Mc/Mac + apostrophe + hyphen handling, non-recursive
- [x] Applied in `web/lib/store-metadata.ts` for `generateMetadata`
- [x] Applied in `web/lib/format.ts` for `formatAddress`/`formatCityState`
- [x] Applied in `web/app/store/[slug]/page.tsx` h1 + breadcrumb
- [x] Rex code review passed (fixed: recursion, unguarded `decodeURIComponent`, apostrophe tail, dead guards, assertion density, prop usage, skeleton, JSON-LD `numberOfItems` consistency)

## What shipped

Merged via `feat/lgs-seo-batch-2` on 2026-04-09. Title-case applied at all public display surfaces. Per-store meta descriptions pull store category, city, and state for rich SERP snippets.
