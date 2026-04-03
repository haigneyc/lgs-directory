# LGS Directory — Bugs To Fix

From Petra's QA pass on 2026-04-02 (main branch after SEO pages merge).

## High

1. **Store names not clickable in city/state tables** — StoreTable on city/state pages has plain text names, no links to `/store/[id]`. Stores are unreachable from the browse flow.
   - Fix: In store table, wrap store name in `<Link href={'/store/' + store.id}>`

2. **Store detail page has generic title** — `<title>` is "LGS Directory" instead of the store name. Kills SEO.
   - Fix: Add `generateMetadata` to `/app/store/[id]/page.tsx` returning `{ title: \`${store.name} | LGS Directory\` }`

## Medium

3. **No LocalBusiness JSON-LD on store detail pages** — State/city pages have it, store detail doesn't.
   - Fix: Add `JsonLd` component with LocalBusiness schema to store detail page

4. **Near Me page has generic title** — Should be "Find Stores Near Me | LGS Directory"
   - Fix: Add metadata export to `/app/near-me/page.tsx`

5. **Homepage table columns cut off on 375px mobile** — Status, WPN, Source columns invisible, no horizontal scroll.

## Low

6. **Out-of-range page silently shows last page** — `?page=999` works but doesn't redirect
7. **Store detail breadcrumb cramped on mobile** — Long store names cause layout issues
