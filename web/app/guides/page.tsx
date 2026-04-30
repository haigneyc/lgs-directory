import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumb } from "@/components/seo/breadcrumb";
import { SITE_URL } from "@/lib/site";
import { getPublishedGuides } from "@/lib/guides";

/** ISO-8601 date → "April 19, 2026"-style display string. */
const DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "long",
  day: "numeric",
});

/** Maximum guides rendered on the index at once (generous headroom). */
const MAX_INDEX_ENTRIES = 200;

const PAGE_TITLE = "Guides";
const PAGE_DESCRIPTION =
  "In-depth guides for local game store owners and collectors — storage, starter sets, tournament prep, and more.";
const CANONICAL_URL = `${SITE_URL}/guides`;

export const metadata: Metadata = {
  title: PAGE_TITLE,
  description: PAGE_DESCRIPTION,
  alternates: { canonical: CANONICAL_URL },
  robots: { index: true, follow: true },
  openGraph: {
    title: PAGE_TITLE,
    description: PAGE_DESCRIPTION,
    type: "website",
    url: CANONICAL_URL,
    siteName: "Roll For Store",
  },
  twitter: {
    card: "summary",
    title: PAGE_TITLE,
    description: PAGE_DESCRIPTION,
  },
};

/**
 * Format an ISO-8601 date string for display. Returns the original
 * string if parsing fails — defensive rather than throwing on a bad
 * frontmatter entry, since a malformed date should not take the whole
 * index down.
 */
function formatPublishedDate(iso: string): string {
  console.assert(typeof iso === "string", "formatPublishedDate: iso must be a string");
  console.assert(iso.length > 0, "formatPublishedDate: iso must be non-empty");
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) {
    return iso;
  }
  return DATE_FORMATTER.format(d);
}

export default function GuidesIndexPage() {
  const guides = getPublishedGuides();
  console.assert(Array.isArray(guides), "GuidesIndexPage: guides must be an array");
  console.assert(
    guides.length <= MAX_INDEX_ENTRIES,
    "GuidesIndexPage: guides exceed index cap",
  );

  const limit = Math.min(guides.length, MAX_INDEX_ENTRIES);

  return (
    <div className="mx-auto max-w-3xl px-4 lg:px-6 py-12">
      <Breadcrumb
        items={[
          { name: "Home", href: "/" },
          { name: "Guides", href: "/guides" },
        ]}
      />

      <header className="mt-6 mb-10">
        <h1 className="font-display text-3xl font-bold tracking-tight bg-gradient-to-r from-stone-100 via-amber-100 to-stone-300 bg-clip-text text-transparent mb-3">
          Guides
        </h1>
        <p className="text-zinc-400 leading-relaxed">{PAGE_DESCRIPTION}</p>
      </header>

      {guides.length === 0 ? (
        <p className="text-sm text-zinc-500 italic">
          No guides published yet. Check back soon.
        </p>
      ) : (
        <ul className="space-y-6">
          {guides.slice(0, limit).map(({ meta }) => (
            <li
              key={meta.slug}
              className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6 hover:border-amber-900/40 transition-colors"
            >
              <Link href={`/guides/${meta.slug}`} className="block group">
                <h2 className="font-display text-xl font-semibold text-zinc-100 group-hover:text-amber-100 transition-colors mb-2">
                  {meta.title}
                </h2>
                <p className="text-sm text-zinc-400 leading-relaxed mb-3">
                  {meta.description}
                </p>
                <p className="text-xs text-zinc-500 uppercase tracking-wider">
                  <time dateTime={meta.publishedAt}>
                    {formatPublishedDate(meta.publishedAt)}
                  </time>
                  <span className="mx-2 text-zinc-700">·</span>
                  <span>{meta.author.name}</span>
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
