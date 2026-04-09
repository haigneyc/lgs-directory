import { NextResponse, type NextRequest } from "next/server";
import { query } from "@/lib/db";

/**
 * Next.js 16 request proxy (formerly known as middleware). Runs before
 * the route handler, so the HTTP status code it returns actually lands
 * on the wire — unlike ``permanentRedirect`` called from inside a
 * ``<Suspense>`` child, which fires after streaming has begun and
 * degrades to a client-side ``router.replace`` that Googlebot cannot
 * see.
 *
 * Sole responsibility: detect legacy ``/store/<uuid>`` URLs, look up
 * the current slug, and emit a real HTTP 308 permanent redirect to
 * ``/store/<slug>``. Everything else (slug URLs, unknown slugs, UUIDs
 * for rows with ``slug IS NULL``) passes through untouched so the
 * existing route handler in ``app/store/[slug]/page.tsx`` owns the
 * response.
 *
 * Bug history: prior to this file, the redirect lived in
 * ``resolveSlugParam`` inside the page body, which ran inside a
 * Suspense boundary. Petra's QA on 2026-04-08 caught that UUID URLs
 * were returning HTTP 200 with ``x-matched-path: /store/[slug]`` and
 * no ``Location`` header, so Googlebot was indexing the UUID URLs as
 * live pages instead of following the redirect to the slug URL.
 */

// RFC 4122 v1-v5 UUID shape. Inlined (rather than imported from
// ``@/lib/slugs``) to keep the proxy module's import graph tight:
// slugs.ts pulls in the full state-abbreviation tables and kebab-case
// helpers that the proxy does not need.
const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/**
 * Minimum plausible store-path shape: ``/store/<token>`` where
 * ``<token>`` is the first segment after ``/store/``. We only care
 * about the first segment; anything trailing is forwarded unchanged
 * by ``NextResponse.next()``.
 */
const STORE_PATH_PREFIX = "/store/";

/**
 * Fetch ONLY the slug column for a given store id. Deliberately does
 * NOT reuse ``getStore`` from ``@/lib/queries`` because that function
 * is decorated with the Next.js ``"use cache"`` directive and
 * ``cacheLife``/``cacheTag`` — Cache Components primitives that are
 * not available inside the proxy runtime. A direct single-column
 * lookup is also cheaper than pulling the full store row plus
 * presences when all we need is the slug.
 *
 * Returns:
 *   - ``string`` — the slug to redirect to
 *   - ``null``    — the row exists but has no slug yet (13 rows as of
 *                   the 2026-04-08 backfill report); caller must pass
 *                   through so the legacy UUID route still serves it
 *   - ``undefined`` — no row matches the id; caller must pass through
 *                     so the route handler emits its own 404
 */
async function lookupSlugForUuid(uuid: string): Promise<string | null | undefined> {
  console.assert(typeof uuid === "string", "lookupSlugForUuid: uuid must be a string");
  console.assert(UUID_REGEX.test(uuid), "lookupSlugForUuid: uuid must match UUID regex");

  const rows = await query<{ slug: string | null }>(
    "SELECT slug FROM stores WHERE id = $1 LIMIT 1",
    [uuid]
  );
  if (rows.length === 0) {
    return undefined;
  }
  const slug = rows[0].slug;
  console.assert(slug === null || typeof slug === "string", "lookupSlugForUuid: slug must be string or null");
  return slug;
}

export default async function proxy(request: NextRequest): Promise<NextResponse> {
  console.assert(request !== null && typeof request === "object", "proxy: request must be an object");
  console.assert(typeof request.nextUrl.pathname === "string", "proxy: pathname must be a string");

  const { pathname } = request.nextUrl;

  // Fast path: only ``/store/<token>`` URLs are candidates. Anything
  // else — including ``/stores/...`` (note the plural), ``/store``
  // with no trailing segment, static assets — returns immediately
  // with zero DB cost. The matcher below also scopes us to this
  // prefix, but the explicit check is defensive and cheap.
  if (!pathname.startsWith(STORE_PATH_PREFIX)) {
    return NextResponse.next();
  }

  // Extract the first path segment after ``/store/``. Trailing
  // segments (none exist today on this route but might in the future)
  // are preserved on the pass-through, and ignored on the redirect
  // since a UUID shouldn't have any.
  const rest = pathname.slice(STORE_PATH_PREFIX.length);
  const slashIdx = rest.indexOf("/");
  const firstSegment = slashIdx >= 0 ? rest.slice(0, slashIdx) : rest;

  // Fast path: slug URLs (the common case) skip the DB round-trip.
  if (!UUID_REGEX.test(firstSegment)) {
    return NextResponse.next();
  }

  // UUID detected — look up the slug. Any unexpected DB error must
  // not break the page; fall through to the route handler, which will
  // render whatever it can (including its own 404) instead of turning
  // every UUID request into a 500.
  let slug: string | null | undefined;
  try {
    slug = await lookupSlugForUuid(firstSegment);
  } catch (err) {
    console.error("proxy: slug lookup failed", err);
    return NextResponse.next();
  }

  // Pass-through cases: row missing, or row exists with slug IS NULL
  // (the 13 un-backfilled stores flagged in commit f51e163). Either
  // way, the route handler in ``app/store/[slug]/page.tsx`` owns the
  // response — 404 for the missing case, UUID-served page for the
  // null-slug case.
  if (slug === undefined || slug === null) {
    return NextResponse.next();
  }
  console.assert(slug.length > 0, "proxy: resolved slug must be non-empty");

  // Build the redirect URL relative to the current request so that
  // host, protocol, and any forwarding headers are preserved across
  // preview/production deployments.
  const redirectUrl = new URL(`/store/${slug}`, request.url);
  return NextResponse.redirect(redirectUrl, 308);
}

/**
 * Scope the proxy to the store detail route only. This keeps the
 * regex check (and on UUID matches, the DB round-trip) off of every
 * request to the site — sitemap, homepage, state pages, static
 * assets, etc. all bypass the proxy entirely.
 *
 * Note the matcher uses the first segment only; deeper nested paths
 * under ``/store/...`` are uncommon today but would still be
 * intercepted, which is desired.
 */
export const config = {
  matcher: "/store/:path*",
};
