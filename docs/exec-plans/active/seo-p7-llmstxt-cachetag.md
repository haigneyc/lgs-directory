# SEO P7 — llms.txt cacheTag for On-Demand Invalidation

**Status:** active
**Priority:** P7
**Owner:** Soren

## Context

`buildLlmsBody` in the llms.txt route uses `cacheLife("hours")` TTL, meaning the store count shown to LLM crawlers can be up to 1 hour stale after a seeder run. Adding `cacheTag("stores")` and calling `revalidateTag("stores")` from the seeder after writing new stores eliminates this staleness.

## Acceptance criteria

- [ ] Add `cacheTag("stores")` inside the `'use cache'` function in `buildLlmsBody`
- [ ] Add a `revalidateTag("stores")` call in the seeder/pipeline entry point after new stores are written
- [ ] Verify `llms.txt` reflects updated store count within seconds of a pipeline run (not up to 1h later)
- [ ] `tsc --noEmit` and `bun run lint` pass

## Notes

- Non-urgent — 1h staleness in llms.txt is not a business-impacting bug
- Pattern mirrors how other `cacheTag("stores")` tags are used in the codebase
- Do NOT use `export const revalidate` — this project uses Cache Components exclusively
- Related files: `web/app/llms.txt/route.ts`, seeder script in Python pipeline
