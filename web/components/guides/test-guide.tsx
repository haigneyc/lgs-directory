import Link from "next/link";
import type { GuideMeta } from "@/lib/guides";

/**
 * Pipeline-verification placeholder. ``draft: true`` keeps this out of
 * the public index, sitemap, and ``getGuideBySlug`` lookup — Googlebot
 * and ordinary visitors cannot reach it. It exists only to let us
 * verify that:
 *
 *   1. ``/guides/`` and ``/guides/[slug]`` render from the registry
 *   2. the FTC disclosure mounts above the body
 *   3. an anchor with ``data-affiliate-network`` +
 *      ``data-affiliate-placement`` flows through the layout-level
 *      ``AffiliateClickTracker`` listener
 *
 * Delete or leave with ``draft: true`` before opening the PR.
 */
export const meta: GuideMeta = {
  slug: "test-guide",
  title: "Guides Pipeline Test",
  description:
    "Placeholder guide used to verify /guides/ routing, disclosure rendering, and affiliate-click tracking. Not for publication.",
  author: { name: "Roll For Store" },
  publishedAt: "2026-04-21",
  disclosure: "amazon-creator-connections",
  draft: true,
};

export default function TestGuide() {
  console.assert(
    meta.slug === "test-guide",
    "TestGuide: meta.slug must match the registry key",
  );
  console.assert(
    meta.draft === true,
    "TestGuide: placeholder must remain a draft",
  );

  return (
    <div className="space-y-4 text-zinc-300 leading-relaxed">
      <p>
        Lorem ipsum dolor sit amet, consectetur adipiscing elit. This
        placeholder post exists so Soren can verify the /guides/ pipeline
        renders end-to-end before Vera&apos;s editorial briefs land.
      </p>

      <p>
        The anchor below is wired with the affiliate tracker data
        attributes. Clicking it should fire a <code>gtag</code>{" "}
        <code>affiliate_click</code> event with{" "}
        <code>network=amazon</code> and{" "}
        <code>placement=guides-test-amazon-link</code>.
      </p>

      <p>
        <Link
          href="https://www.amazon.com/dp/B0EXAMPLE000?tag=orangediscoun-20&linkCode=ll2"
          data-affiliate-network="amazon"
          data-affiliate-placement="guides-test-amazon-link"
          className="inline-flex items-center gap-1 rounded-md bg-yellow-600/20 px-3 py-1.5 text-sm font-medium text-yellow-100 underline underline-offset-2 hover:bg-yellow-600/30 transition-colors"
          rel="sponsored nofollow noopener"
          target="_blank"
        >
          Example Amazon product link (click to fire tracker)
        </Link>
      </p>

      <p>
        Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
        Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris
        nisi ut aliquip ex ea commodo consequat.
      </p>
    </div>
  );
}
