# Backlog — Roll For Store

Ideas and deferred items. Not actively planned. Revisit when traffic justifies the investment.

## Monetization

- **Premium listings ("Claim Your Store")** — $39/mo Stripe integration. Plan complete (13 tasks). Needs Stripe + Supabase billing tables. Unblocked, just deprioritized behind SEO.
- **Display ads (Mediavine Journey)** — threshold: 1,000 sessions/mo. Not there yet. Revisit when organic traffic crosses ~30 impressions/day consistently.
- **TCGPlayer affiliate** — application declined. Reapply when traffic grows to show meaningful click volume.
- **Content marketing blog** — store spotlight posts, game event recaps. Low priority until directory traffic is established.
- **Reddit launch post** — one-time channel. Save for when the directory has 10k+ stores or a notable feature (events page).

## Data / Pipeline

- **Composite index on `store_external_refs`** — if provider-filtered queries get slow, add `(store_id, provider)` index. Non-urgent at current data size.
- **Dead systemd timers cleanup** — LGS systemd timers were created but may need reinstallation after server maintenance. Audit and reinstall if daily sync shows gaps.
- **Foursquare OS bulk download** — daily timer exists; verify it's running and producing useful new stores.

## Features

- **Event aggregation** — turn rollforstore into a weekly destination by aggregating game events (Magic prereleases, FGC tournaments, Warhammer game nights). Full plan at `/home/chris/jarvis/Outbox/2026-04-06/rollforstore-event-aggregation-plan.md`. Revisit trigger: monthly impressions exceed ~500/day in GSC, OR Chris hits a "rollforstore feels stalled" moment in Aug–Oct 2026.
  - Critical first move when revisited: reprocess Petra's existing `store_external_refs.payload` rows (provider=`website_content`) through a one-shot Claude Haiku extractor to count latent events already on disk. If 500–2k → moat thesis validated.
- **Store owner outreach for backlinks** — manual campaign. Deprioritized until organic traffic proves SEO viability.

## SEO

- **`/stores/page.tsx:93` numberOfItems** — uses `sorted.length` instead of `itemListElements.length`. Rex flagged as cosmetic; only diverges if states exceed 60 (practically impossible).
- **Resubmit sitemap in GSC** — manual step for Chris after any major URL structure change.

## Directory Expansion

From Marie's research (2026-04-03) — all rated for fit/opportunity:

- CrossFit/Functional Fitness Gyms (8/10) — scrapable affiliate list
- Independent Bookstores (7/10) — Bookshop.org 10% affiliate
- Tattoo Studios (7/10) — style-based discovery gap
- Specialty Butcher Shops (7/10) — USDA data is public
- Martial Arts / BJJ (6/10) — IBJJF academy list
- Makerspaces (6/10) — small market but zero competition
