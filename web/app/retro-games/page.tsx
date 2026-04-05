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
import { Gamepad2 } from "lucide-react";

export const revalidate = 86400;

const CATEGORY = getCategoryRouteBySlug("retro-games")!;
console.assert(CATEGORY !== null, "retro-games category route must exist");

export const metadata: Metadata = {
  title: CATEGORY.title,
  description: CATEGORY.description,
  openGraph: {
    title: CATEGORY.title,
    description: CATEGORY.description,
    type: "website",
    url: `${SITE_URL}/retro-games`,
  },
};

interface PageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function RetroGamesPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const requestedPage =
    typeof params.page === "string" ? Number.parseInt(params.page, 10) : 1;
  const rawPage = Number.isFinite(requestedPage) ? requestedPage : 1;
  const state = typeof params.state === "string" ? params.state : undefined;

  const safePage = Math.max(1, rawPage);
  console.assert(safePage >= 1, "RetroGamesPage: page must be >= 1");

  const [result, topCities] = await Promise.all([
    listStoresByCategory(CATEGORY.dbCategory, { page: safePage, state }),
    getTopCitiesForCategory(CATEGORY.dbCategory),
  ]);

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: CATEGORY.label, href: "/retro-games" },
  ];

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
    <div className="mx-auto max-w-7xl px-4 lg:px-6 py-8">
      <Breadcrumb items={breadcrumbItems} />

      <div className="mb-8 mt-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-green-500/10 text-green-400">
            <Gamepad2 className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-display text-2xl font-bold tracking-tight">
              {CATEGORY.label}
            </h1>
            <p className="text-sm text-zinc-500">
              {result.total.toLocaleString()} stores
            </p>
          </div>
        </div>
        <p className="text-sm text-zinc-400 max-w-2xl mt-2 leading-relaxed">
          {CATEGORY.heroText}
        </p>
        <a
          href={EBAY_URLS.collections.boardGames}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-lg border border-yellow-600/30 bg-yellow-600/5 text-sm font-medium text-yellow-400 hover:text-yellow-300 hover:bg-yellow-600/10 hover:border-yellow-500/50 transition-all duration-200"
        >
          Shop Retro Games &amp; Consoles on eBay →
        </a>
      </div>

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

      {topCities.length > 0 && (
        <CategoryTopCities categoryLabel={CATEGORY.label} cities={topCities} />
      )}

      <JsonLd data={{
        "@context": "https://schema.org",
        "@type": "ItemList",
        name: CATEGORY.label,
        description: CATEGORY.description,
        numberOfItems: result.total,
        itemListElement: itemListElements,
      }} />
    </div>
  );
}
