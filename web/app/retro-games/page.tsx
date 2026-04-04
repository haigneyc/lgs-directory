import { Suspense } from "react";
import type { Metadata } from "next";
import { listStoresByCategory } from "@/lib/queries";
import { StoreTable } from "@/components/store-table";
import { Pagination } from "@/components/pagination";
import { Breadcrumb } from "@/components/seo/breadcrumb";
import { JsonLd } from "@/components/seo/json-ld";
import { getCategoryRouteBySlug } from "@/lib/category-routes";
import { SITE_URL } from "@/lib/site";

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

  const result = await listStoresByCategory(CATEGORY.dbCategory, {
    page: safePage,
    state,
  });

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
    <div className="mx-auto max-w-7xl px-4 py-8">
      <Breadcrumb items={breadcrumbItems} />

      <div className="mb-6 mt-4">
        <h1 className="text-2xl font-semibold tracking-tight mb-1">
          {CATEGORY.label}
        </h1>
        <p className="text-sm text-zinc-400 max-w-2xl">
          {CATEGORY.heroText}
        </p>
      </div>

      <p className="text-zinc-500 text-sm mb-4">
        {result.total} stores found
      </p>

      <div className="rounded-lg border border-zinc-800 bg-zinc-950">
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
    </div>
  );
}
