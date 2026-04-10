# Amazon Associates — 90-Day Deadline

**Status:** active
**Priority:** P1 (hard deadline)
**Owner:** Chris (manual — traffic/conversion problem, not a code problem)

## Context

Amazon Associates account `orangediscoun-20` needs 3 qualifying purchases within 180 days of sign-up. The warning email arrived 2026-04-06, giving roughly until 2026-07-06. Infrastructure is fully shipped (30 affiliate links across 4 shelves on rollforstore.com, 44 links across 8 shelves on findmylfs.com). This is now a traffic/conversion problem.

## Acceptance criteria

- [ ] 3 qualifying Amazon purchases made via `orangediscoun-20` affiliate links before 2026-07-06
- [ ] Self-purchases do NOT count (Amazon TOS ban on personal orders)
- [ ] Organic traffic conversion or friends-and-family ask are the two realistic paths

## Notes

- Infrastructure shipped 2026-04-06: `tag=orangediscoun-20` enforced with runtime assert in `AmazonShelf` component, FTC disclosure on 3 surfaces per site, `/affiliate-disclosure` page live
- Link pattern uses SEARCH queries not ASINs to avoid link rot
- Constants + builders at `web/lib/amazon.ts`
- **Self-purchases are banned by Amazon TOS** — do not try it
- Friends-and-family ask is the most realistic near-term save: ask 8-10 people to click through before their next Amazon order
- If account closes: reapply immediately. Infrastructure is already built for the next account
- rollforstore was at ~19 impressions/day in early April — organic conversion alone is unlikely to hit 3 purchases in time
