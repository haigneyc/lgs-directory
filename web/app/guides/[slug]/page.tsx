import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Breadcrumb } from "@/components/seo/breadcrumb";
import { JsonLd } from "@/components/seo/json-ld";
import { FTCDisclosure } from "@/components/ftc-disclosure";
import { SITE_URL } from "@/lib/site";
import {
  getAllGuides,
  getGuideBySlug,
  guideCanonicalUrl,
  type GuideEntry,
} from "@/lib/guides";

const DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "long",
  day: "numeric",
});

/** Upper bound for ``generateStaticParams`` — matches registry cap. */
const MAX_STATIC_PARAMS = 500;

interface PageProps {
  params: Promise<{ slug: string }>;
}

/**
 * Cache Components friendly: the registry is fully static, so we
 * prerender every registered slug — including drafts — at build time.
 * Draft entries still 404 at request time because ``getGuideBySlug``
 * returns ``null`` for them, which triggers ``notFound()`` before the
 * body streams. Next.js 16 Cache Components rejects empty
 * ``generateStaticParams`` results, so while the registry is sparse
 * (pilot launch) we keep drafts in the params list to guarantee the
 * array is non-empty; the public index and sitemap still honour
 * ``draft: true`` via ``getPublishedGuides``.
 */
export function generateStaticParams(): Array<{ slug: string }> {
  const all = getAllGuides();
  console.assert(Array.isArray(all), "generateStaticParams: guides must be an array");
  console.assert(
    all.length <= MAX_STATIC_PARAMS,
    "generateStaticParams: registry exceeds static-params cap",
  );
  console.assert(
    all.length > 0,
    "generateStaticParams: registry must contain at least one entry (Cache Components requirement)",
  );

  const out: Array<{ slug: string }> = [];
  const limit = Math.min(all.length, MAX_STATIC_PARAMS);
  for (let i = 0; i < limit; i += 1) {
    out.push({ slug: all[i].meta.slug });
  }
  return out;
}

/** Absolute, protocol-prefixed OG image URL or ``undefined``. */
function resolveHeroImage(hero: string | undefined): string | undefined {
  console.assert(
    hero === undefined || typeof hero === "string",
    "resolveHeroImage: hero must be a string or undefined",
  );
  console.assert(
    SITE_URL.startsWith("https://"),
    "resolveHeroImage: SITE_URL must be absolute",
  );
  if (hero === undefined || hero.length === 0) {
    return undefined;
  }
  if (hero.startsWith("http://") || hero.startsWith("https://")) {
    return hero;
  }
  const path = hero.startsWith("/") ? hero : `/${hero}`;
  return `${SITE_URL}${path}`;
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { slug } = await params;
  console.assert(typeof slug === "string", "generateMetadata: slug must be a string");
  console.assert(slug.length > 0, "generateMetadata: slug must be non-empty");

  const entry = getGuideBySlug(slug);
  if (entry === null) {
    // Matches ``/store/[slug]`` prior art: triggering ``notFound()``
    // from metadata sets HTTP 404 before the page body runs, preventing
    // Cache Components from locking in a 200 response.
    notFound();
  }

  const canonical = guideCanonicalUrl(entry.meta.slug);
  const hero = resolveHeroImage(entry.meta.heroImage);

  return {
    title: entry.meta.title,
    description: entry.meta.description,
    alternates: { canonical },
    robots: { index: true, follow: true },
    authors: [{ name: entry.meta.author.name, url: entry.meta.author.url }],
    openGraph: {
      title: entry.meta.title,
      description: entry.meta.description,
      type: "article",
      url: canonical,
      siteName: "Roll For Store",
      publishedTime: entry.meta.publishedAt,
      modifiedTime: entry.meta.updatedAt ?? entry.meta.publishedAt,
      authors: [entry.meta.author.name],
      images: hero !== undefined ? [{ url: hero }] : undefined,
    },
    twitter: {
      card: hero !== undefined ? "summary_large_image" : "summary",
      title: entry.meta.title,
      description: entry.meta.description,
      images: hero !== undefined ? [hero] : undefined,
    },
  };
}

/**
 * ``Article`` structured data. Kept in this module (not lifted to
 * ``lib/``) because it's only used here and the shape is short enough
 * to audit at a glance.
 */
function buildArticleJsonLd(entry: GuideEntry): Record<string, unknown> {
  console.assert(entry !== null, "buildArticleJsonLd: entry must not be null");
  console.assert(
    typeof entry.meta.title === "string",
    "buildArticleJsonLd: title must be a string",
  );

  const canonical = guideCanonicalUrl(entry.meta.slug);
  const hero = resolveHeroImage(entry.meta.heroImage);

  const data: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Article",
    "@id": canonical,
    headline: entry.meta.title,
    description: entry.meta.description,
    datePublished: entry.meta.publishedAt,
    dateModified: entry.meta.updatedAt ?? entry.meta.publishedAt,
    mainEntityOfPage: { "@type": "WebPage", "@id": canonical },
    author: {
      "@type": "Person",
      name: entry.meta.author.name,
      ...(entry.meta.author.url !== undefined ? { url: entry.meta.author.url } : {}),
    },
    publisher: {
      "@type": "Organization",
      name: "Roll For Store",
      url: SITE_URL,
    },
  };

  if (hero !== undefined) {
    data.image = hero;
  }

  return data;
}

function formatDisplayDate(iso: string): string {
  console.assert(typeof iso === "string", "formatDisplayDate: iso must be a string");
  console.assert(iso.length > 0, "formatDisplayDate: iso must be non-empty");
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) {
    return iso;
  }
  return DATE_FORMATTER.format(d);
}

export default async function GuideDetailPage({ params }: PageProps) {
  const { slug } = await params;
  console.assert(typeof slug === "string", "GuideDetailPage: slug must be a string");
  console.assert(slug.length > 0, "GuideDetailPage: slug must be non-empty");

  const entry = getGuideBySlug(slug);
  if (entry === null) {
    notFound();
  }

  const { meta, Component } = entry;
  const showUpdated =
    typeof meta.updatedAt === "string" && meta.updatedAt !== meta.publishedAt;

  return (
    <article className="mx-auto max-w-3xl px-4 lg:px-6 py-12">
      <Breadcrumb
        items={[
          { name: "Home", href: "/" },
          { name: "Guides", href: "/guides" },
          { name: meta.title, href: `/guides/${meta.slug}` },
        ]}
      />

      <header className="mt-6 mb-6">
        <h1 className="font-display text-3xl lg:text-4xl font-bold tracking-tight text-zinc-100 mb-3">
          {meta.title}
        </h1>
        <p className="text-sm text-zinc-500">
          By <span className="text-zinc-300">{meta.author.name}</span>
          <span className="mx-2 text-zinc-700">·</span>
          <time dateTime={meta.publishedAt}>
            {formatDisplayDate(meta.publishedAt)}
          </time>
          {showUpdated && meta.updatedAt !== undefined && (
            <>
              <span className="mx-2 text-zinc-700">·</span>
              <span className="italic">
                Updated{" "}
                <time dateTime={meta.updatedAt}>
                  {formatDisplayDate(meta.updatedAt)}
                </time>
              </span>
            </>
          )}
        </p>
      </header>

      {meta.disclosure !== undefined && (
        <FTCDisclosure campaign={meta.disclosure} />
      )}

      {/*
       * `prose-invert` flips the default light palette to a dark-mode
       * palette (white text on dark bg). `prose-lg` bumps body copy to
       * 18px / 1.78 line-height -- matches the long-form-article rhythm
       * Chris uses elsewhere on the site. The `prose-a:*` overrides
       * make affiliate anchors visibly distinct from body copy: the
       * default `prose-invert` link color is too close to body text on
       * `bg-zinc-950`, which made the MORCCO affiliate link disappear
       * entirely (Dash diagnosis 2026-04-21).
       */}
      <div className="prose prose-invert prose-lg max-w-none prose-a:text-amber-300 prose-a:font-medium prose-a:underline prose-a:decoration-amber-500/40 prose-a:underline-offset-2 hover:prose-a:text-amber-200 prose-a:transition-colors">
        <Component />
      </div>

      <JsonLd data={buildArticleJsonLd(entry)} />
    </article>
  );
}
