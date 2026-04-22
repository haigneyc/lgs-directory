import type { ComponentType } from "react";
import type { FTCDisclosureCampaign } from "@/components/ftc-disclosure";
import { SITE_URL } from "@/lib/site";

/**
 * Guide registry for ``/guides/[slug]``.
 *
 * Rationale (Soren 2026-04-21): the repo does not currently process
 * ``.mdx`` or raw markdown, and the CLAUDE.md directive explicitly
 * discourages adding a dependency without reason. A typed TS registry
 * keeps guides fully static-renderable (Cache Components friendly),
 * gives editors a frontmatter-shaped object to populate, and lets the
 * sitemap + index page import the same source of truth the detail route
 * uses.
 *
 * Each guide is a TSX file under ``components/guides/<slug>.tsx`` that
 * exports two things:
 *
 *   1. A named ``meta`` constant matching ``GuideMeta`` below (title,
 *      description, publishedAt, etc.). This is the "frontmatter".
 *   2. A default-exported React component rendering the post body.
 *
 * The files are imported and registered in ``GUIDES_MODULES`` in this
 * file. Adding a new guide = new file + one registry entry. No magic,
 * no filesystem scanning at build time.
 */

/**
 * Author attribution. Used in metadata and Article JSON-LD.
 */
export interface GuideAuthor {
  name: string;
  url?: string;
}

/**
 * Frontmatter-shaped metadata attached to every guide module.
 *
 * Dates are ISO-8601 strings (``YYYY-MM-DD``). Slug matches the
 * registry key below and the ``/guides/<slug>`` URL segment.
 */
export interface GuideMeta {
  slug: string;
  title: string;
  description: string;
  author: GuideAuthor;
  publishedAt: string;
  updatedAt?: string;
  /** Optional absolute or relative image URL used for OG + JSON-LD. */
  heroImage?: string;
  /** Which FTC disclosure campaign to render above the post body. */
  disclosure?: FTCDisclosureCampaign;
  /**
   * Set to ``true`` to hide from ``/guides/`` index, sitemap, and
   * ``getPublishedGuides``. The placeholder pipeline-test guide uses
   * this so it never ships to production even if the file is left in
   * place by accident.
   */
  draft?: boolean;
  /**
   * Short list of category labels ("Collectibles", "TCG", etc.). Used
   * for future filtering. No runtime behavior today.
   */
  tags?: readonly string[];
}

/**
 * A registered guide: its frontmatter plus the body component.
 */
export interface GuideEntry {
  meta: GuideMeta;
  Component: ComponentType;
}

import LargeTcgCollectionStorage, {
  meta as largeTcgCollectionStorageMeta,
} from "@/components/guides/large-tcg-collection-storage";

/**
 * All registered guide modules. New guides land here. The order in this
 * array defines the order used by ``getPublishedGuides`` as a
 * tiebreaker when publish dates match.
 */
const GUIDES_MODULES: readonly GuideEntry[] = [
  {
    meta: largeTcgCollectionStorageMeta,
    Component: LargeTcgCollectionStorage,
  },
] as const;

/**
 * Maximum guides we ever expect to have in this registry. Serves as
 * the fixed upper bound for every loop over ``GUIDES_MODULES`` per the
 * CLAUDE.md "all loops have fixed upper bounds" rule.
 */
const MAX_GUIDES = 500;

/**
 * Return every registered guide, including drafts. Useful for tooling
 * and internal preview contexts; NOT what the public index should use.
 */
export function getAllGuides(): readonly GuideEntry[] {
  console.assert(
    Array.isArray(GUIDES_MODULES),
    "getAllGuides: GUIDES_MODULES must be an array",
  );
  console.assert(
    GUIDES_MODULES.length <= MAX_GUIDES,
    "getAllGuides: registry size exceeded sanity cap",
  );
  return GUIDES_MODULES;
}

/**
 * Return the published, non-draft guides sorted newest-first by
 * ``publishedAt``. Use this for the ``/guides`` index, sitemap, and
 * any public listing.
 */
export function getPublishedGuides(): readonly GuideEntry[] {
  console.assert(
    Array.isArray(GUIDES_MODULES),
    "getPublishedGuides: GUIDES_MODULES must be an array",
  );
  console.assert(
    GUIDES_MODULES.length <= MAX_GUIDES,
    "getPublishedGuides: registry size exceeded sanity cap",
  );

  const out: GuideEntry[] = [];
  const limit = Math.min(GUIDES_MODULES.length, MAX_GUIDES);
  for (let i = 0; i < limit; i += 1) {
    const entry = GUIDES_MODULES[i];
    if (entry.meta.draft !== true) {
      out.push(entry);
    }
  }
  out.sort((a, b) => b.meta.publishedAt.localeCompare(a.meta.publishedAt));
  return out;
}

/**
 * Look up a guide by slug. Returns ``null`` when the slug is unknown
 * or belongs to a draft (drafts are not reachable at runtime, same as
 * the published-only indexer above).
 */
export function getGuideBySlug(slug: string): GuideEntry | null {
  console.assert(
    typeof slug === "string",
    "getGuideBySlug: slug must be a string",
  );
  console.assert(
    slug.length > 0,
    "getGuideBySlug: slug must be non-empty",
  );

  const normalized = slug.toLowerCase();
  const limit = Math.min(GUIDES_MODULES.length, MAX_GUIDES);
  for (let i = 0; i < limit; i += 1) {
    const entry = GUIDES_MODULES[i];
    if (entry.meta.slug === normalized && entry.meta.draft !== true) {
      return entry;
    }
  }
  return null;
}

/**
 * Canonical absolute URL for a guide. Centralised so the [slug] page,
 * index page, sitemap, and JSON-LD all agree.
 */
export function guideCanonicalUrl(slug: string): string {
  console.assert(
    typeof slug === "string" && slug.length > 0,
    "guideCanonicalUrl: slug must be a non-empty string",
  );
  console.assert(
    SITE_URL.startsWith("https://"),
    "guideCanonicalUrl: SITE_URL must be absolute",
  );
  return `${SITE_URL}/guides/${slug}`;
}
