# ADR-006: Amazon Associates Integration

**Date:** 2026-04-09
**Status:** accepted

## Context

Roll For Store needs affiliate revenue to offset running costs (~$200/mo Claude + Vercel). Amazon Associates is the lowest-friction affiliate program and has relevant product categories (TCG supplies, Warhammer paints, retro gaming gear, comic storage).

## Decision

Implement Amazon affiliate shelves using the `orangediscoun-20` Associates tag. Four shelves deployed on store pages:
- TCG Essentials
- Warhammer Painter's Bench
- Retro Gaming Gear
- Comic Collector Storage

**Tag enforcement:** The `AmazonShelf` component has a runtime assert that the `tag` prop equals `orangediscoun-20`. This prevents accidental link rot if the constant is ever updated — a mismatch fails loudly rather than silently serving non-monetized links.

**Link pattern — search queries, not ASINs.** Links use Amazon search URLs rather than specific ASIN product URLs. Specific ASINs go out of stock or are delisted; search URLs remain valid and surface current inventory. This avoids the ongoing maintenance burden of curating and updating individual product links.

**FTC disclosure:** Required by FTC regulations. Disclosure appears on 3 surfaces: site footer, per-shelf inline disclosure, and a dedicated `/affiliate-disclosure` page. All three are required for compliant disclosure — do not remove any surface.

**90-day qualification deadline:** Amazon Associates account `orangediscoun-20` was warned on 2026-04-06 that the account will close if it hasn't driven 3 qualifying purchases within 180 days of signup (deadline ~2026-07-06). Infrastructure is shipped; conversion at current traffic (~19 impressions/day) is the constraint.

**Self-purchases are banned by Amazon TOS.** Do not attempt self-qualifying purchases.

**Shared account:** The same `orangediscoun-20` tag is used across both rollforstore.com and findmylfs.com. The 3-purchase threshold is account-wide, so both sites contribute.

## Consequences

- 30 affiliate links across 4 shelves on rollforstore.com.
- See also lfs-locator ADR-001 for the parallel implementation on findmylfs.com.
- If the account closes: reapply immediately. Infrastructure persists, second account starts ahead of where first did.

## Notes

- See `web/lib/amazon.ts` for the tag constant and link builders.
- See `web/app/affiliate-disclosure/page.tsx` for the disclosure page.
- See `/home/chris/.claude/projects/-home-chris-jarvis/memory/project_amazon_associates_deadline.md` for the deadline context.
