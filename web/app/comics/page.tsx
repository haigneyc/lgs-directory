import { Suspense } from "react";
import type { Metadata } from "next";
import { listStoresByCategory, getTopCitiesForCategory } from "@/lib/queries";
import { StoreTable } from "@/components/store-table";
import { Pagination } from "@/components/pagination";
import { Breadcrumb } from "@/components/seo/breadcrumb";
import { JsonLd } from "@/components/seo/json-ld";
import { getCategoryRouteBySlug } from "@/lib/category-routes";
import { CategoryTopCities } from "@/components/category-top-cities";
import { SITE_URL, EBAY_URLS } from "@/lib/site";
import { AffiliateDisclosure } from "@/components/affiliate-disclosure";
import { AmazonShelf } from "@/components/amazon/amazon-shelf";
import { SHELVES } from "@/lib/amazon-shelves";
import { AffiliateLink } from "@/components/affiliate-link";
import { BookOpen } from "lucide-react";
import { StoreTableSkeleton } from "@/components/store-table-skeleton";

const CATEGORY = getCategoryRouteBySlug("comics")!;
console.assert(CATEGORY !== null, "comics category route must exist");

const COMICS_TITLE = "Comic Book Store Near Me | Comic Shops Near Me | Roll For Store";
const COMICS_DESCRIPTION =
  "Find a comic book store near me and compare comic shops near me with Roll For Store. Browse local comic shops, LCS favorites, graded comics, comic preservation supplies, and comic grading services.";
const COMICS_H1 = "Comic Book Store Near Me? Browse Comic Shops Near Me";

export const metadata: Metadata = {
  title: COMICS_TITLE,
  description: COMICS_DESCRIPTION,
  openGraph: {
    title: COMICS_TITLE,
    description: COMICS_DESCRIPTION,
    type: "website",
    url: `${SITE_URL}/comics`,
  },
};

interface PageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

/**
 * Synchronous page shell — MUST NOT await anything. Awaiting searchParams
 * at the top level would opt the entire route into dynamic rendering and
 * defeat the edge-cache fix (PERF-026). The unresolved `searchParams`
 * Promise is forwarded to the async child below, which is the only place
 * in this file permitted to await it.
 */
export default function ComicsPage({ searchParams }: PageProps) {
  console.assert(typeof searchParams === "object", "ComicsPage: searchParams must be an object (Promise)");
  console.assert(CATEGORY !== null, "ComicsPage: CATEGORY must be resolved");

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: CATEGORY.label, href: "/comics" },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 lg:px-6 py-8">
      <Breadcrumb items={breadcrumbItems} />
      <ComicsHeroSection />
      <ComicsHighlightsSection />

      <Suspense fallback={<StoreTableSkeleton />}>
        <DynamicStoreSection searchParams={searchParams} />
      </Suspense>

      <div className="mt-10">
        <AmazonShelf
          shelf={SHELVES["comics-storage"]}
          placement="comics-bottom-shelf"
        />
      </div>

      <ComicsClusterCopySection />

      <Suspense fallback={null}>
        <TopCitiesSection />
      </Suspense>
    </div>
  );
}

function ComicsHeroSection() {
  console.assert(CATEGORY !== null, "ComicsHeroSection: CATEGORY must be resolved");
  console.assert(COMICS_H1.includes("Comic"), "ComicsHeroSection: heading must reference comic intent");

  return (
    <div className="mb-8 mt-6">
      <div className="flex items-center gap-3 mb-2">
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-cyan-500/10 text-cyan-400">
          <BookOpen className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight">
            {COMICS_H1}
          </h1>
        </div>
      </div>
      <p className="text-sm text-zinc-400 max-w-3xl mt-2 leading-relaxed">
        Find local comic shops by city and state, then compare weekly pull-list stops, back-issue rooms, and comic book stores carrying graphic novels, collectibles, and graded comics.
      </p>
      <p className="text-sm text-zinc-400 max-w-3xl mt-3 leading-relaxed">
        Use this comics hub when you need a dependable LCS for new releases, comic preservation supplies, or comic grading services before you prep a convention run or a slab submission.
      </p>
      <AffiliateLink
        href={EBAY_URLS.collections.comics}
        network="ebay"
        placement="comics-cta"
        className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-lg border border-yellow-600/30 bg-yellow-600/5 text-sm font-medium text-yellow-400 hover:text-yellow-300 hover:bg-yellow-600/10 hover:border-yellow-500/50 transition-all duration-200"
      >
        Shop Comics &amp; Collectibles on eBay →
      </AffiliateLink>
      <AffiliateDisclosure className="mt-1.5" />
    </div>
  );
}

function ComicsHighlightsSection() {
  console.assert(SHELVES["comics-storage"].links.length >= 4, "ComicsHighlightsSection: comics shelf needs at least four links");
  console.assert(COMICS_DESCRIPTION.includes("comic grading services"), "ComicsHighlightsSection: metadata should cover grading-services intent");

  return (
    <>
      <div className="mb-8">
        <AmazonShelf
          shelf={SHELVES["comics-storage"]}
          placement="comics-above-fold-shelf"
          variant="strip"
        />
      </div>

      <section className="mb-8 grid gap-4 lg:grid-cols-2">
        <article className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
          <h2 className="font-display text-lg font-semibold text-zinc-200">
            Compare comic book stores before the next pull-list run
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-zinc-400">
            The best comic book stores blend weekly releases with knowledgeable staff, organized back-issue bins, and event calendars that keep an LCS anchored in its local scene. This directory helps you sort comic shops near you before you commit to a drive across town.
          </p>
        </article>
        <article className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
          <h2 className="font-display text-lg font-semibold text-zinc-200">
            Graded comics, comic preservation, and comic grading services
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-zinc-400">
            Serious collectors usually need more than a new-release wall. Keep long boxes, bags and boards, mylar sleeves, and slab storage close at hand, then use local comic shops to source graded comics or confirm which stores handle comic grading services and convention prep.
          </p>
        </article>
      </section>
    </>
  );
}

function ComicsClusterCopySection() {
  console.assert(COMICS_DESCRIPTION.includes("comic book store near me"), "ComicsClusterCopySection: metadata should cover the primary query");
  console.assert(COMICS_DESCRIPTION.includes("comic shops near me"), "ComicsClusterCopySection: metadata should cover the secondary query");

  return (
    <section className="mt-10 rounded-xl border border-zinc-800 bg-zinc-900/40 p-5">
      <h2 className="font-display text-lg font-semibold text-zinc-200">
        Use local comic shops as the offline side of your collection workflow
      </h2>
      <p className="mt-3 max-w-4xl text-sm leading-relaxed text-zinc-400">
        A strong LCS is where you can preview variants, talk through creator runs, and sanity-check grading decisions before you ship a key issue. Pair the directory with the comic preservation shelf above when you need supplies for short-term reading boxes, archival storage, or graded-comic handoff days.
      </p>
    </section>
  );
}

/**
 * Async child component — the ONLY place that awaits searchParams. Keeping
 * this awaited read out of the top-level page lets the shell prerender.
 */
async function DynamicStoreSection({
  searchParams,
}: Readonly<{
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}>) {
  const params = await searchParams;
  console.assert(typeof params === "object", "DynamicStoreSection: params must be an object");

  const requestedPage =
    typeof params.page === "string" ? Number.parseInt(params.page, 10) : 1;
  const rawPage = Number.isFinite(requestedPage) ? requestedPage : 1;
  const state = typeof params.state === "string" ? params.state : undefined;

  const safePage = Math.max(1, rawPage);
  console.assert(safePage >= 1, "DynamicStoreSection: page must be >= 1");

  const result = await listStoresByCategory(CATEGORY.dbCategory, {
    page: safePage,
    state,
  });

  const MAX_JSON_LD = 25;
  const jsonLdLimit = Math.min(result.stores.length, MAX_JSON_LD);
  const itemListElements: Record<string, unknown>[] = [];
  for (let i = 0; i < jsonLdLimit; i++) {
    const store = result.stores[i];
    itemListElements.push({
      "@type": "ListItem",
      position: i + 1,
      item: {
        "@type": "LocalBusiness",
        name: store.name,
        address: {
          "@type": "PostalAddress",
          streetAddress: store.address.street,
          addressLocality: store.address.city,
          addressRegion: store.address.state,
          postalCode: store.address.zip_code,
        },
      },
    });
  }

  return (
    <>
      <p className="text-sm text-zinc-500 mb-2">
        {result.total.toLocaleString()} stores
      </p>
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/30">
        <StoreTable stores={result.stores} />
      </div>
      <Suspense fallback={null}>
        <Pagination
          page={result.page}
          pageSize={result.pageSize}
          total={result.total}
        />
      </Suspense>
      <JsonLd data={{
        "@context": "https://schema.org",
        "@type": "ItemList",
        name: CATEGORY.label,
        description: COMICS_DESCRIPTION,
        numberOfItems: result.total,
        itemListElement: itemListElements,
      }} />
    </>
  );
}

/**
 * Async child for top-cities module. Does NOT depend on searchParams, so
 * it prerenders at build time as part of the shell.
 */
async function TopCitiesSection() {
  const topCities = await getTopCitiesForCategory(CATEGORY.dbCategory);
  console.assert(Array.isArray(topCities), "TopCitiesSection: topCities must be an array");
  console.assert(topCities.length >= 0, "TopCitiesSection: topCities length must be non-negative");
  if (topCities.length === 0) {
    return null;
  }
  return <CategoryTopCities categoryLabel={CATEGORY.label} cities={topCities} />;
}
