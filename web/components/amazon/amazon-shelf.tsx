/**
 * AmazonShelf — server-rendered card of curated Amazon affiliate links.
 *
 * Each shelf renders the required Amazon Associates disclosure inline, in
 * addition to the global footer disclosure, so the disclosure travels with
 * the cluster of links per Amazon's Operating Agreement.
 *
 * All links use rel="sponsored noopener noreferrer" so search engines treat
 * them as paid placements per Google's link attribution guidelines.
 */

import { ShoppingBag } from "lucide-react";
import { buildAmazonSearchLink, AMAZON_DISCLOSURE_TEXT } from "@/lib/amazon";
import type { ShelfDefinition } from "@/lib/amazon-shelves";

interface AmazonShelfProps {
  shelf: ShelfDefinition;
  /** When true, render a tighter variant suited for the homepage bottom. */
  compact?: boolean;
}

const MAX_LINKS_FULL = 8;
const MAX_LINKS_COMPACT = 6;

export function AmazonShelf({ shelf, compact = false }: AmazonShelfProps) {
  console.assert(shelf !== null && shelf !== undefined, "AmazonShelf: shelf required");
  console.assert(typeof shelf.title === "string", "AmazonShelf: shelf.title must be a string");
  console.assert(Array.isArray(shelf.links), "AmazonShelf: shelf.links must be an array");
  console.assert(shelf.links.length > 0, "AmazonShelf: shelf must have at least one link");
  console.assert(typeof compact === "boolean", "AmazonShelf: compact must be a boolean");

  const limit = compact ? MAX_LINKS_COMPACT : MAX_LINKS_FULL;
  const displayed = shelf.links.slice(0, limit);
  console.assert(displayed.length > 0, "AmazonShelf: displayed must not be empty");

  return (
    <section
      aria-label={shelf.title}
      className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6"
    >
      <div className="flex items-center gap-3 mb-2">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-yellow-600/10 text-yellow-500">
          <ShoppingBag className="w-4 h-4" />
        </div>
        <h2 className="font-display font-semibold text-zinc-200">{shelf.title}</h2>
      </div>
      <p className="text-sm text-zinc-500 mb-4 leading-relaxed">{shelf.intro}</p>

      <ul className="divide-y divide-zinc-800/80 rounded-lg border border-zinc-800/80 bg-zinc-950/40">
        {displayed.map((link) => {
          const href = buildAmazonSearchLink(link.query);
          console.assert(href.includes("tag=orangediscoun-20"), "AmazonShelf: link missing tag");
          return (
            <li key={link.query} className="px-4 py-3">
              <a
                href={href}
                target="_blank"
                rel="sponsored noopener noreferrer"
                className="group flex items-start justify-between gap-4"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-zinc-200 group-hover:text-yellow-400 transition-colors">
                    {link.title}
                  </p>
                  <p className="text-xs text-zinc-500 mt-0.5 leading-relaxed">
                    {link.blurb}
                  </p>
                </div>
                <span className="text-xs font-medium text-zinc-500 group-hover:text-yellow-400 transition-colors whitespace-nowrap mt-0.5">
                  Shop ↗
                </span>
              </a>
            </li>
          );
        })}
      </ul>

      <p className="text-xs text-zinc-500 italic mt-4">{AMAZON_DISCLOSURE_TEXT}</p>
    </section>
  );
}
