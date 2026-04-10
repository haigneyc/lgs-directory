# ADR-005: Title-Case for All-Caps Strings Only

**Date:** 2026-04-09
**Status:** accepted

## Context

WPN (Wizards of the Coast) data supplies store names in ALL CAPS for a significant fraction of stores (e.g., `GAME NITE`, `THE GATHERING PLACE`). Displaying these in the UI looks unprofessional. A title-casing transform was needed.

Two options were considered:
1. **Universal title-case** — transform all strings regardless of their current casing.
2. **All-caps only** — transform only strings that are entirely uppercase; leave mixed-case strings unchanged.

## Decision

Apply title-case only to strings that are detected as all-caps (`str === str.toUpperCase()`). Leave mixed-case strings unchanged.

Rationale: Many stores intentionally use mixed-case brand names (e.g., `moxen`, `eXtreme Games`, `PoP Culture`). A universal title-case transform would corrupt these deliberate brand choices. Limiting the transform to all-caps-only strings is safe: an all-caps string from WPN data is almost certainly an artifact of their data entry convention, not an intentional brand choice.

**Acronym allowlist:** Known gaming acronyms are preserved after title-casing: MTG, TCG, RPG, D&D, LGS, FNM, CCG, GW, WPN, FGC. These would be incorrectly lowercased by a naive title-case algorithm.

**Special handling:**
- `Mc`/`Mac` prefixes: next character is uppercased (`McDonald` not `Mcdonald`).
- Hyphenated strings: each segment is title-cased independently.
- Apostrophes: character after apostrophe is uppercased (`O'Brien` not `O'brien`).
- Non-recursive implementation — the transform is a single-pass string function with no internal recursion.

## Consequences

- Mixed-case brand names are preserved exactly as stored.
- All-caps WPN names are normalized to readable title case in store titles, metadata, breadcrumbs, and address formatting.
- Applied at display time via `web/lib/display-case.ts` — not written back to the database.

## Notes

- See `web/lib/display-case.ts` for implementation.
- Applied in: `web/lib/store-metadata.ts`, `web/lib/format.ts` (formatAddress/formatCityState), `web/app/store/[slug]/page.tsx` (h1 + breadcrumb).
- See `web/docs/seo-decisions.md` — Per-Store Metadata section.
