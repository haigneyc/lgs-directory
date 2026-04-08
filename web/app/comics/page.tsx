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
import { BookOpen } from "lucide-react";
import { StoreTableSkeleton } from "@/components/store-table-skeleton";

export const revalidate = 86400;

const CATEGORY = getCategoryRouteBySlug("comics")!;
console.assert(CATEGORY !== null, "comics category route must exist");

export const metadata: Metadata = {
  title: CATEGORY.title,
  description: CATEGORY.description,
  openGraph: {
    title: CATEGORY.title,
    description: CATEGORY.description,
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

      <div className="mb-8 mt-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-cyan-500/10 text-cyan-400">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-display text-2xl font-bold tracking-tight">
              {CATEGORY.label}
            </h1>
          </div>
        </div>
        <p className="text-sm text-zinc-400 max-w-2xl mt-2 leading-relaxed">
          {CATEGORY.heroText}
        </p>
        <a
          href={EBAY_URLS.collections.comics}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-lg border border-yellow-600/30 bg-yellow-600/5 text-sm font-medium text-yellow-400 hover:text-yellow-300 hover:bg-yellow-600/10 hover:border-yellow-500/50 transition-all duration-200"
        >
          Shop Comics &amp; Collectibles on eBay →
        </a>
        <AffiliateDisclosure className="mt-1.5" />
      </div>

      <Suspense fallback={<StoreTableSkeleton />}>
        <DynamicStoreSection searchParams={searchParams} />
      </Suspense>

      <div className="mt-10">
        <AmazonShelf shelf={SHELVES["comics-storage"]} />
      </div>

      <Suspense fallback={null}>
        <TopCitiesSection />
      </Suspense>
    </div>
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

  // JSON-LD ItemList
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
        description: CATEGORY.description,
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
  if (topCities.length === 0) {
    return null;
  }
  return <CategoryTopCities categoryLabel={CATEGORY.label} cities={topCities} />;
}
