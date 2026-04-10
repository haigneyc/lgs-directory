# Trust Filter — Games Workshop + Hawaii Fix

**Status:** completed
**Shipped:** 2026-04-09
**Owner:** Soren

## Context

Two data quality fixes shipped as part of the 2026-04-09 batch: (1) Games Workshop stores properly filtered/classified in the trust system; (2) Hawaii stores were incorrectly excluded or misclassified due to a state-code handling bug.

## Acceptance criteria

- [x] Games Workshop stores appear correctly in `/warhammer` category with proper trust scoring
- [x] Hawaii stores (state code `HI`) render correctly on state and city pages
- [x] Trust filter in `listStores` (`TRUSTED_CANDIDATE_FILTER` in `lib/queries.ts`) remains intact

## What shipped

Shipped 2026-04-09. GW filter ensures Games Workshop–sourced stores pass the trust threshold. Hawaii fix corrected state-code normalization that was causing HI stores to fall through a filter gap.
