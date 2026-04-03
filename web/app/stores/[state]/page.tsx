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
import type { StoreWithDistance } from "@/lib/types";

export const revalidate = 86400;

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
    return { title: "Not Found | Roll For Store" };
  }

  const abbrev = slugToAbbreviation(stateSlug);
  const initialResult = await listStores({ state: abbrev ?? undefined });

  const title = `Game Stores in ${stateName} | Roll For Store`;
  const description = `Browse ${initialResult.total} local game stores in ${stateName}. Find WPN-certified stores, online sellers, and more.`;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: "website",
      url: `https://rollforstore.com/stores/${stateSlug}`,
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

export default async function StatePage({ params, searchParams }: Readonly<PageProps>) {
  const { state: stateSlug } = await params;
  const sp = await searchParams;

  const stateName = slugToState(stateSlug);
  if (stateName === null) {
    notFound();
  }

  const abbrev = slugToAbbreviation(stateSlug);
  console.assert(typeof stateName === "string", "StatePage: stateName must be a string");
  console.assert(abbrev !== null, "StatePage: abbrev must not be null for a valid state");

  const rawPage = typeof sp.page === "string" ? parseInt(sp.page, 10) : 1;

  const [initialResult, cities, stateStats] = await Promise.all([
    listStores({ state: abbrev ?? undefined, page: rawPage }),
    getCityIndex(abbrev ?? stateName),
    getStateIndex(),
  ]);

  // Clamp page to valid range so out-of-range pages show the last valid page
  const totalPages = Math.ceil(initialResult.total / initialResult.pageSize) || 1;
  const safePage = Math.min(Math.max(1, rawPage), totalPages);

  // Re-fetch with clamped page only if the requested page was out of range
  const result =
    safePage === rawPage
      ? initialResult
      : await listStores({ state: abbrev ?? undefined, page: safePage });

  // Build StoreWithDistance[] for the map — add distance_miles: 0
  const storesWithCoords: StoreWithDistance[] = [];
  const storeLimit = Math.min(result.stores.length, 500);
  for (let i = 0; i < storeLimit; i++) {
    const store = result.stores[i];
    if (store.latitude !== null && store.longitude !== null) {
      storesWithCoords.push({ ...store, distance_miles: 0 });
    }
  }

  // Use first store with coordinates as map center
  const centerLat = storesWithCoords.length > 0 ? storesWithCoords[0].latitude! : 39.8283;
  const centerLng = storesWithCoords.length > 0 ? storesWithCoords[0].longitude! : -98.5795;

  // Look up accurate stats from getStateIndex (aggregated server-side)
  const currentStats = stateStats.find(
    (s) => s.slug === stateSlug
  );
  const storeCount = currentStats?.store_count ?? result.total;
  const activeCount = currentStats?.active_count ?? 0;
  const wpnPremiumCount = currentStats?.wpn_premium_count ?? 0;
  const onlineCount = currentStats?.online_count ?? 0;

  // Build JSON-LD ItemList of LocalBusiness (first 25 stores)
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

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: stateName, href: `/stores/${stateSlug}` },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <Breadcrumb items={breadcrumbItems} />

      <div className="mb-6 mt-4">
        <h1 className="text-2xl font-semibold tracking-tight mb-1">
          Game Stores in {stateName}
        </h1>
      </div>

      <StatsBar
        storeCount={storeCount}
        activeCount={activeCount}
        wpnPremiumCount={wpnPremiumCount}
        onlineCount={onlineCount}
      />

      {storesWithCoords.length > 0 && (
        <div className="mb-8">
          <div className="rounded-lg border border-zinc-800 overflow-hidden h-96 bg-zinc-900">
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

      {cities.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-medium mb-3">
            Cities in {stateName}
          </h2>
          <CityGrid stateSlug={stateSlug} cities={cities} />
        </div>
      )}

      <div className="mb-8">
        <h2 className="text-lg font-medium mb-3">
          All Stores in {abbrev}
        </h2>
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
      </div>

      <JsonLd data={jsonLdData} />
    </div>
  );
}
