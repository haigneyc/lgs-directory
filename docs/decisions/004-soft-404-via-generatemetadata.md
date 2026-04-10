# ADR-004: Soft-404 via notFound() in generateMetadata

**Date:** 2026-04-09
**Status:** accepted

## Context

In Next.js 16 with Cache Components, `generateMetadata` resolves **before** the page body begins rendering. If `generateMetadata` returns a metadata object for a not-found case (e.g., `{ title: "Store Not Found" }`) and only the page body calls `notFound()`, the HTTP status is committed at 200 before the page body's `notFound()` can take effect.

Google soft-penalizes pages that return HTTP 200 with thin or empty content ("soft 404"). A store page that no longer exists but returns 200 costs ranking signal and can pollute the sitemap.

## Decision

Call `notFound()` from `generateMetadata` for any store lookup that fails. Do not return a metadata object for the not-found case.

```typescript
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const slug = (await params).slug;
  const store = await getStore(slug);
  if (!store) {
    notFound(); // ← call here, not just in page body
  }
  return buildStoreMetadata(store);
}
```

This is a behavior change from earlier Next.js versions where metadata was rendered independently of the page body. In Next.js 16 with Cache Components, the first resolver to commit the HTTP status wins — and `generateMetadata` runs first.

## Consequences

- Missing store slugs return HTTP 404 (not 200) for both Googlebot and users.
- The 404 page is rendered — users see a clear error state, not an empty page.
- `notFound()` in `generateMetadata` is sufficient; the page body can also call it for defense-in-depth, but it is not load-bearing in Next.js 16.

## Notes

- See `web/app/store/[slug]/page.tsx` for implementation.
- See `web/docs/seo-decisions.md` — Soft-404 Handling section (covers the same rule from the SEO perspective; this ADR adds the Next.js 16 implementation rationale).
- This applies to all dynamic routes with database lookups (`/store/[slug]`, `/stores/[state]/[city]`, etc.).
- Reference: `/home/chris/.claude/projects/-home-chris-jarvis/memory/reference_next16_cache_components.md` — "Metadata-first resolution causes soft 404s" section.
