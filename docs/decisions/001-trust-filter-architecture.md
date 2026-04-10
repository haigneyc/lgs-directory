# ADR-001: Trust Filter Architecture

**Date:** 2026-04-09
**Status:** accepted

## Context

Roll For Store ingests stores from multiple sources: WPN, Google Places, Games Workshop, and scraped content. Google Places alone returns thousands of candidates, many of which are not actual local game stores (nail salons, office supply stores, noise from text matching). These candidates need to be suppressed from the public directory until they are validated.

The question was: what constitutes sufficient signal that a candidate is a real, relevant game store?

## Decision

A three-tier trust signal approach was chosen:

1. **WPN registration** (`wpn_id IS NOT NULL`) — direct Wizards of the Coast registration is the strongest possible signal. If a store sells Magic, it is in scope.
2. **Website content scrape** (`store_external_refs` with `provider = 'website_content'` and non-empty products array) — the content scraper visits the store's website and looks for game product references. Positive hit confirms the store carries relevant product.
3. **Games Workshop locator** (`store_external_refs` with `provider = 'games_workshop'`) — the official GW store finder is a high-quality curated source.

Any one of these signals is sufficient to make a candidate publicly visible. Candidates with none of these signals are hidden (`TRUSTED_CANDIDATE_FILTER` in `lib/queries.ts` applied to all `listStores` calls).

The Hawaii precedent: when the filter was first calibrated, removing unverified candidates admitted +1,368 net stores — these were candidates whose quality was confirmed by WPN or GW data but not yet linked. The decision was accepted rather than re-tightened, on the basis that WPN/GW linkage was already authoritative.

GameStop was explicitly kept in the directory despite being a chain: WPN-authorized and increasingly LGS-like in its Magic event hosting. Individual store manager judgment, not a policy exception.

Events-page signal: stores with TCG/FGC events calendar pages (even cafes or bars) are strong positive signals and should boost trust score, potentially overriding cafe/bar suspicion. Not yet implemented as a hard signal in the scoring system (as of 2026-04-09).

## Consequences

- ~4,129 stores publicly visible as of 2026-04-06, out of ~6,117 total candidates.
- Low-quality Google Places candidates are suppressed but not deleted — they can surface if they gain trust signal later.
- The filter must remain in `listStores` — removing it would flood the directory with noise and hurt SEO/trust.
- Ingestion pipeline applies name/types/country blocklist at intake to prevent obvious noise from ever reaching the database.

## Notes

- See `web/lib/queries.ts` `TRUSTED_CANDIDATE_FILTER` for implementation.
- See also `docs/seo-decisions.md` — Trust Filter section for the SEO rationale (soft-404 implications).
- Chain noise (Hobby Lobby, Best Buy, Michaels, FYE) was hard-deleted (~41 rows) on 2026-04-06.
- Re-evaluate events-page signal addition in content scraper when expanding store validation logic.
