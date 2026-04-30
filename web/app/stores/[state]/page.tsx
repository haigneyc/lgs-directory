import { Suspense } from "react";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { slugToState, slugToAbbreviation } from "@/lib/slugs";
import { listStores, getCityIndex, getStateIndex } from "@/lib/queries";
import { Breadcrumb } from "@/components/seo/breadcrumb";
import { JsonLd } from "@/components/seo/json-ld";
import { StatsBar } from "@/components/stats-bar";
import { StoreTable } from "@/components/store-table";
import { Pagination } from "@/components/pagination";
import { CityGrid } from "@/components/city-grid";
import { StoreMapLazy } from "@/components/map/store-map-lazy";
import { SITE_URL } from "@/lib/site";
import { MapPin } from "lucide-react";
import type { StoreWithDistance } from "@/lib/types";
import { StoreTableSkeleton } from "@/components/store-table-skeleton";
import { DirectoryAffiliateSection } from "@/components/directory-affiliate-section";
import {
  StateHeaderSkeleton,
  StateStatsSkeleton,
} from "@/components/directory-page-skeletons";

interface PageProps {
  params: Promise<{ state: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export async function generateMetadata(
  { params }: Readonly<Pick<PageProps, "params">>
): Promise<Metadata> {
  const { state: stateSlug } = await params;
  const stateName = slugToState(stateSlug);

  console.assert(typeof stateSlug === "string", "generateMetadata: stateSlug must be a string");
  console.assert(stateSlug.length > 0, "generateMetadata: stateSlug must not be empty");

  if (stateName === null) {
    return { title: "Not Found", robots: { index: false, follow: true } };
  }

  const abbrev = slugToAbbreviation(stateSlug);
  const initialResult = await listStores({ state: abbrev ?? undefined });

  const title = `Game Stores in ${stateName}`;
  const description = `Browse ${initialResult.total} local game stores in ${stateName}. Find WPN-certified stores, online sellers, and more.`;
  const canonical = `${SITE_URL}/stores/${stateSlug}`;

  return {
    title,
    description,
    alternates: { canonical },
    robots: { index: true, follow: true },
    openGraph: {
      title,
      description,
      type: "website",
      url: canonical,
      siteName: "Roll For Store",
    },
  };
}

export async function generateStaticParams(): Promise<{ state: string }[]> {
  const states = await getStateIndex();

  console.assert(Array.isArray(states), "generateStaticParams: states must be an array");
  console.assert(states.length >= 0, "generateStaticParams: states length must be non-negative");

  const result: { state: string }[] = [];
  const limit = Math.min(states.length, 60);
  for (let i = 0; i < limit; i++) {
    result.push({ state: states[i].slug });
  }
  return result;
}

const MAX_JSON_LD_ITEMS = 25;

/**
 * Synchronous shell — MUST NOT await anything (PERF-026). Both `params`
 * and `searchParams` are forwarded to async children as unresolved
 * Promises. The shell itself renders only static chrome so it can be
 * prerendered and cached at the edge.
 */
export default function StatePage({ params, searchParams }: Readonly<PageProps>) {
  console.assert(typeof params === "object", "StatePage: params must be an object (Promise)");
  console.assert(typeof searchParams === "object", "StatePage: searchParams must be an object (Promise)");

  return (
    <div className="mx-auto max-w-7xl px-4 lg:px-6 py-8">
      <Suspense fallback={<StateHeaderSkeleton />}>
        <StaticStateHeader params={params} />
      </Suspense>

      <Suspense fallback={<StateStatsSkeleton />}>
        <StaticStateStats params={params} />
      </Suspense>

      <Suspense fallback={<StoreTableSkeleton />}>
        <DynamicStoresSection params={params} searchParams={searchParams} />
      </Suspense>

      <DirectoryAffiliateSection placementBase="state-directory" />

    </div>
  );
}

/**
 * Header block — depends only on params, not searchParams. Prerenders
 * for any state slug in generateStaticParams.
 */
async function StaticStateHeader({
  params,
}: Readonly<{ params: Promise<{ state: string }> }>) {
  const { state: stateSlug } = await params;
  const stateName = slugToState(stateSlug);
  if (stateName === null) {
    notFound();
  }

  console.assert(typeof stateSlug === "string" && stateSlug.length > 0, "StaticStateHeader: stateSlug must be non-empty");
  console.assert(typeof stateName === "string", "StaticStateHeader: stateName must be a string");

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: stateName, href: `/stores/${stateSlug}` },
  ];

  return (
    <>
      <Breadcrumb items={breadcrumbItems} />
      <div className="mb-6 mt-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-yellow-600/10 text-yellow-500">
            <MapPin className="w-5 h-5" />
          </div>
          <h1 className="font-display text-2xl font-bold tracking-tight">
            Game Stores in {stateName}
          </h1>
        </div>
      </div>
    </>
  );
}

/**
 * Stats + city grid — depends on params only, not searchParams. Also
 * prerenderable.
 */
async function StaticStateStats({
  params,
}: Readonly<{ params: Promise<{ state: string }> }>) {
  const { state: stateSlug } = await params;
  const stateName = slugToState(stateSlug);
  if (stateName === null) {
    return null;
  }

  const abbrev = slugToAbbreviation(stateSlug);
  console.assert(abbrev !== null, "StaticStateStats: abbrev must not be null");

  const [cities, stateStats] = await Promise.all([
    getCityIndex(abbrev ?? stateName),
    getStateIndex(),
  ]);

  const currentStats = stateStats.find((s) => s.slug === stateSlug);
  const storeCount = currentStats?.store_count ?? 0;
  const activeCount = currentStats?.active_count ?? 0;
  const wpnPremiumCount = currentStats?.wpn_premium_count ?? 0;
  const onlineCount = currentStats?.online_count ?? 0;

  console.assert(Array.isArray(cities), "StaticStateStats: cities must be an array");

  return (
    <>
      <StatsBar
        storeCount={storeCount}
        activeCount={activeCount}
        wpnPremiumCount={wpnPremiumCount}
        onlineCount={onlineCount}
      />

      {cities.length > 0 && (
        <div className="mb-8">
          <h2 className="font-display text-lg font-semibold mb-4">
            Cities in {stateName}
          </h2>
          <CityGrid stateSlug={stateSlug} cities={cities} />
        </div>
      )}
    </>
  );
}

/**
 * Paginated store listing + map + JSON-LD — depends on searchParams so
 * it streams in as a dynamic hole under the static shell.
 */
async function DynamicStoresSection({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ state: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}>) {
  const { state: stateSlug } = await params;
  const sp = await searchParams;

  const stateName = slugToState(stateSlug);
  if (stateName === null) {
    notFound();
  }

  const abbrev = slugToAbbreviation(stateSlug);
  console.assert(typeof stateName === "string", "DynamicStoresSection: stateName must be a string");
  console.assert(abbrev !== null, "DynamicStoresSection: abbrev must not be null for a valid state");

  const rawPage = typeof sp.page === "string" ? parseInt(sp.page, 10) : 1;

  const initialResult = await listStores({ state: abbrev ?? undefined, page: rawPage });

  const totalPages = Math.ceil(initialResult.total / initialResult.pageSize) || 1;
  const safePage = Math.min(Math.max(1, rawPage), totalPages);

  const result =
    safePage === rawPage
      ? initialResult
      : await listStores({ state: abbrev ?? undefined, page: safePage });

  const storesWithCoords: StoreWithDistance[] = [];
  const storeLimit = Math.min(result.stores.length, 500);
  for (let i = 0; i < storeLimit; i++) {
    const store = result.stores[i];
    if (store.latitude !== null && store.longitude !== null) {
      storesWithCoords.push({ ...store, distance_miles: 0 });
    }
  }

  const centerLat = storesWithCoords.length > 0 ? storesWithCoords[0].latitude! : 39.8283;
  const centerLng = storesWithCoords.length > 0 ? storesWithCoords[0].longitude! : -98.5795;

  const jsonLdLimit = Math.min(result.stores.length, MAX_JSON_LD_ITEMS);
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
        ...(store.latitude !== null && store.longitude !== null
          ? {
              geo: {
                "@type": "GeoCoordinates",
                latitude: store.latitude,
                longitude: store.longitude,
              },
            }
          : {}),
      },
    });
  }

  const jsonLdData: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: `Game Stores in ${stateName}`,
    numberOfItems: result.total,
    itemListElement: itemListElements,
  };

  return (
    <>
      {storesWithCoords.length > 0 && (
        <div className="mb-8">
          <div className="rounded-xl border border-zinc-800 overflow-hidden h-96 bg-zinc-900">
            <Suspense
              fallback={
                <div className="h-full w-full flex items-center justify-center">
                  <p className="text-zinc-500 text-sm">Loading map...</p>
                </div>
              }
            >
              <StoreMapLazy
                stores={storesWithCoords}
                userLat={centerLat}
                userLng={centerLng}
              />
            </Suspense>
          </div>
        </div>
      )}

      <div className="mb-8">
        <h2 className="font-display text-lg font-semibold mb-4">
          All Stores in {abbrev}
        </h2>
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
      </div>

      <JsonLd data={jsonLdData} />
    </>
  );
}
