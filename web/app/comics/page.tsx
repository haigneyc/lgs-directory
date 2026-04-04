import { Suspense } from "react";
import type { Metadata } from "next";
import { listStoresByCategory } from "@/lib/queries";
import { StoreTable } from "@/components/store-table";
import { Pagination } from "@/components/pagination";
import { Breadcrumb } from "@/components/seo/breadcrumb";
import { JsonLd } from "@/components/seo/json-ld";
import { getCategoryRouteBySlug } from "@/lib/category-routes";
import { SITE_URL } from "@/lib/site";
import { BookOpen } from "lucide-react";

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

export default async function ComicsPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const requestedPage =
    typeof params.page === "string" ? Number.parseInt(params.page, 10) : 1;
  const rawPage = Number.isFinite(requestedPage) ? requestedPage : 1;
  const state = typeof params.state === "string" ? params.state : undefined;

  const safePage = Math.max(1, rawPage);
  console.assert(safePage >= 1, "ComicsPage: page must be >= 1");

  const result = await listStoresByCategory(CATEGORY.dbCategory, {
    page: safePage,
    state,
  });

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: CATEGORY.label, href: "/comics" },
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
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-cyan-500/10 text-cyan-400">
            <BookOpen className="w-5 h-5" />
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
