# SEO P5 — getTotalStoreCount Filter Discrepancy

**Status:** active
**Priority:** P5
**Owner:** Soren

## Context

`getTotalStoreCount()` in `web/lib/queries.ts` returns ~4,100 stores but the sitemap has 6,117 entries. The cause is a `TRUSTED_CANDIDATE_FILTER` WHERE-clause mismatch — the total count query applies trust filtering but the sitemap does not (or vice versa). This causes `llms.txt` to under-report the directory size. Non-blocking for SEO but creates misleading metadata.

## Acceptance criteria

- [ ] Identify which query is wrong: `getTotalStoreCount()` or the sitemap query
- [ ] Align both so they use the same filter logic
- [ ] Verify `llms.txt` reports a number consistent with the sitemap count
- [ ] No change to publicly visible store count (trust filter must remain in `listStores`)

## Notes

- `TRUSTED_CANDIDATE_FILTER` lives in `web/lib/queries.ts` — do NOT remove it from `listStores`
- The discrepancy is ~2,000 stores: likely stores that have slugs but don't pass the trust filter
- Non-urgent: sitemap is correct, only `llms.txt` is wrong
- Related files: `web/lib/queries.ts`, `web/app/llms.txt/route.ts`
