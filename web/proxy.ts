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

/**
 * Module-level slug cache. Rex review 2026-04-08 flagged the prior
 * per-request `SELECT EXISTS` as a real Supavisor round-trip
 * regression on the hot path (6,100 stores, every request). Tradeoff:
 *
 *   - Option A (unstable_cache / cacheTag): not available inside the
 *     proxy runtime — Cache Components primitives are route-level only.
 *   - Option B (Vercel Runtime Cache API): works, but adds a network
 *     hop per miss, which on warm instances is worse than a Set lookup.
 *   - Option C (module-level Set with TTL refresh): chosen. On Fluid
 *     Compute warm instances the Set persists across invocations, so
 *     the amortised cost of a slug existence check is an in-memory
 *     ~hash lookup. On cold starts we pay one `SELECT slug FROM stores`
 *     (6k rows, single round trip, ~50ms). New stores take up to
 *     SLUG_CACHE_TTL_MS to become reachable, which is acceptable —
 *     the publish cadence is slower than 5 minutes.
 *
 * All slugs are stored lowercase so the lookup is case-insensitive
 * (Rex concern 5); the DB schema canonicalises slugs to lowercase
 * already, but defence in depth is cheap.
 */
const SLUG_CACHE_TTL_MS = 5 * 60 * 1000;

interface SlugCache {
  set: Set<string>;
  loadedAt: number;
}

let slugCache: SlugCache | null = null;
let slugCacheInflight: Promise<SlugCache> | null = null;

async function loadSlugCache(): Promise<SlugCache> {
  const rows = await query<{ slug: string | null }>(
    "SELECT slug FROM stores WHERE slug IS NOT NULL AND status <> 'closed'"
  );
  console.assert(Array.isArray(rows), "loadSlugCache: rows must be an array");
  const set = new Set<string>();
  const MAX_ROWS = 100_000;
  const rowCount = rows.length;
  console.assert(rowCount <= MAX_ROWS, "loadSlugCache: row count exceeds sanity cap");
  for (let i = 0; i < rowCount && i < MAX_ROWS; i += 1) {
    const s = rows[i].slug;
    if (typeof s === "string" && s.length > 0) {
      set.add(s.toLowerCase());
    }
  }
  return { set, loadedAt: Date.now() };
}

async function getSlugCache(): Promise<SlugCache> {
  const now = Date.now();
  if (slugCache !== null && now - slugCache.loadedAt < SLUG_CACHE_TTL_MS) {
    return slugCache;
  }
  if (slugCacheInflight !== null) {
    return slugCacheInflight;
  }
  slugCacheInflight = loadSlugCache()
    .then((fresh) => {
      slugCache = fresh;
      return fresh;
    })
    .finally(() => {
      slugCacheInflight = null;
    });
  return slugCacheInflight;
}

/**
 * Cheap existence check for a store slug. Backed by a module-level
 * Set with TTL refresh — see the comment on `SLUG_CACHE_TTL_MS` above
 * for the caching tradeoff. Case-insensitive by design.
 */
async function storeSlugExists(slug: string): Promise<boolean> {
  console.assert(typeof slug === "string", "storeSlugExists: slug must be a string");
  console.assert(slug.length > 0, "storeSlugExists: slug must be non-empty");
  console.assert(slug.length <= 200, "storeSlugExists: slug suspiciously long");

  const cache = await getSlugCache();
  console.assert(cache.set instanceof Set, "storeSlugExists: cache.set must be a Set");
  return cache.set.has(slug.toLowerCase());
}

/**
 * Build a 404 NextResponse. Body is intentionally empty — Next.js's
 * own `not-found.tsx` cannot run from the proxy layer, but the status
 * is what crawlers actually consume. The Content-Type is set so curl
 * and browsers don't choke on the empty body.
 */
function notFoundResponse(): NextResponse {
  return new NextResponse("Not Found", {
    status: 404,
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      // Allow the CDN to cache bad-slug 404s briefly so a spray of
      // crawler hits doesn't hammer the proxy, but expire fast enough
      // that a backfilled slug becomes reachable within minutes
      // (Rex concern 4, 2026-04-08).
      "Cache-Control": "public, max-age=0, s-maxage=60, stale-while-revalidate=300",
    },
  });
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

  // Slug URL branch: verify the slug exists in the DB before letting
  // the page handler run. Without this gate, unknown slugs leak HTTP
  // 200 with the static homepage shell — Cache Components prerenders
  // the shell with status 200 and `notFound()` from inside the route
  // cannot retroactively flip the status (Petra QA 2026-04-08).
  if (!UUID_REGEX.test(firstSegment)) {
    let exists: boolean;
    try {
      exists = await storeSlugExists(firstSegment);
    } catch (err) {
      // On DB error, fall through and let the page handler try. We
      // never want a transient DB blip to turn every store URL into
      // a 404.
      console.error("proxy: slug existence check failed", err);
      return NextResponse.next();
    }
    if (!exists) {
      return notFoundResponse();
    }
    return NextResponse.next();
  }

  // UUID detected — look up the slug. Any unexpected DB error must
  // not break the page; fall through to the route handler, which will
  // render whatever it can instead of turning every UUID request into
  // a 500.
  let slug: string | null | undefined;
  try {
    slug = await lookupSlugForUuid(firstSegment);
  } catch (err) {
    console.error("proxy: slug lookup failed", err);
    return NextResponse.next();
  }

  // Row missing entirely → real HTTP 404 (Petra QA 2026-04-08).
  if (slug === undefined) {
    return notFoundResponse();
  }
  // Row exists with slug IS NULL (the ~13 un-backfilled stores flagged
  // in commit f51e163). Pass through so the legacy UUID URL still
  // serves the page from `app/store/[slug]/page.tsx`.
  if (slug === null) {
    return NextResponse.next();
  }
  console.assert(slug.length > 0, "proxy: resolved slug must be non-empty");

  // Build the redirect URL by cloning request.nextUrl and mutating
  // only the pathname. Cloning preserves host, protocol, AND search
  // params automatically — the prior `new URL(path, base)` form was
  // dropping query strings on the redirect, which silently broke UTM
  // attribution on UUID-tagged share links (caught by Petra QA).
  const dest = request.nextUrl.clone();
  dest.pathname = `/store/${slug}`;
  return NextResponse.redirect(dest, 308);
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
