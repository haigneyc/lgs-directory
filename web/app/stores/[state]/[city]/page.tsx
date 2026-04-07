import { Suspense } from "react";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { slugToState, slugToAbbreviation, slugToCity, stateToSlug, cityToSlug } from "@/lib/slugs";
import { listStores, getOnlineStores, getNearbyCities, getCityDescription, getStoreEnrichments, getPopularCities } from "@/lib/queries";
import { Breadcrumb } from "@/components/seo/breadcrumb";
import { JsonLd } from "@/components/seo/json-ld";
import { StatsBar } from "@/components/stats-bar";
import { StoreTable } from "@/components/store-table";
import { Pagination } from "@/components/pagination";
import { OnlineStoresCard } from "@/components/online-stores-card";
import { NearbyCities } from "@/components/nearby-cities";
import { StoreMapLazy } from "@/components/map/store-map-lazy";
import { SITE_URL } from "@/lib/site";
import type { StoreWithDistance } from "@/lib/types";

export const revalidate = 86400;

/** Upper bound on prerendered city pages — keeps build time bounded. */
const TOP_CITIES_PRERENDER_LIMIT = 300;

/**
 * Prerender the top ~300 (city, state) combinations at build time. These
 * are the cities linked from the homepage "Popular Cities" module and
 * receive most of the `/stores/[state]/[city]` traffic. All other city
 * pages stay on ISR on-demand. Per Nox QW-8 / PERF-001.
 */
export async function generateStaticParams(): Promise<Array<{ state: string; city: string }>> {
  const cities = await getPopularCities(TOP_CITIES_PRERENDER_LIMIT);
  console.assert(Array.isArray(cities), "generateStaticParams: cities must be an array");
  console.assert(cities.length <= TOP_CITIES_PRERENDER_LIMIT, "generateStaticParams: cities exceeded limit");

  const params: Array<{ state: string; city: string }> = [];
  const max = Math.min(cities.length, TOP_CITIES_PRERENDER_LIMIT);
  for (let i = 0; i < max; i++) {
    const row = cities[i];
    if (!row.state || !row.city) {
      continue;
    }
    params.push({
      state: stateToSlug(row.state),
      city: cityToSlug(row.city),
    });
  }
  return params;
}

interface PageProps {
  params: Promise<{ state: string; city: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export async function generateMetadata(
  { params }: Readonly<Pick<PageProps, "params">>
): Promise<Metadata> {
  const { state: stateSlug, city: citySlug } = await params;
  const stateName = slugToState(stateSlug);

  console.assert(typeof stateSlug === "string", "generateMetadata: stateSlug must be a string");
  console.assert(typeof citySlug === "string", "generateMetadata: citySlug must be a string");

  if (stateName === null) {
    return { title: "Not Found | Roll For Store" };
  }

  const abbrev = slugToAbbreviation(stateSlug);
  const cityName = slugToCity(citySlug);
  const initialResult = await listStores({ state: abbrev ?? undefined, city: cityName });

  if (initialResult.total === 0) {
    return { title: "Not Found | Roll For Store" };
  }

  const title = `Game Stores in ${cityName}, ${abbrev} | Roll For Store`;
  const description = `Browse ${initialResult.total} local game stores in ${cityName}, ${abbrev}. Find WPN-certified stores, online sellers, and more.`;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: "website",
      url: `${SITE_URL}/stores/${stateSlug}/${citySlug}`,
    },
  };
}

const MAX_JSON_LD_ITEMS = 25;

export default async function CityPage({ params, searchParams }: Readonly<PageProps>) {
  const { state: stateSlug, city: citySlug } = await params;
  const sp = await searchParams;

  const stateName = slugToState(stateSlug);
  if (stateName === null) {
    notFound();
  }

  const abbrev = slugToAbbreviation(stateSlug);
  const cityName = slugToCity(citySlug);

  console.assert(typeof stateName === "string", "CityPage: stateName must be a string");
  console.assert(abbrev !== null, "CityPage: abbrev must not be null for a valid state");

  const rawPage = typeof sp.page === "string" ? parseInt(sp.page, 10) : 1;

  const stateDbName = abbrev ?? stateName;
  const [initialResult, onlineStores, nearbyCities, cityDescription] = await Promise.all([
    listStores({ state: abbrev ?? undefined, city: cityName, page: rawPage }),
    getOnlineStores(stateDbName, cityName),
    getNearbyCities(stateDbName, cityName),
    getCityDescription(stateDbName, cityName),
  ]);

  if (initialResult.total === 0) {
    notFound();
  }

  // Clamp page to valid range so out-of-range pages show the last valid page
  const totalPages = Math.ceil(initialResult.total / initialResult.pageSize) || 1;
  const safePage = Math.min(Math.max(1, rawPage), totalPages);

  // Re-fetch with clamped page only if the requested page was out of range
  const result =
    safePage === rawPage
      ? initialResult
      : await listStores({ state: abbrev ?? undefined, city: cityName, page: safePage });

  // Fetch enrichments for stores on this page
  const storeIds = result.stores.map((s) => s.id);
  const enrichments = await getStoreEnrichments(storeIds);

  // Compute stats inline from the result
  const activeCount = result.stores.filter(
    (s) => s.status === "active" || s.status === "verified"
  ).length;
  const premiumCount = result.stores.filter(
    (s) => s.wpn_level === "premium"
  ).length;

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
    "@type": "CollectionPage",
    name: `Game Stores in ${cityName}, ${abbrev}`,
    url: `${SITE_URL}/stores/${stateSlug}/${citySlug}`,
    mainEntity: {
      "@type": "ItemList",
      numberOfItems: result.total,
      itemListElement: itemListElements,
    },
  };

  const breadcrumbItems = [
    { name: "Home", href: "/" },
    { name: stateName, href: `/stores/${stateSlug}` },
    { name: cityName, href: `/stores/${stateSlug}/${citySlug}` },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 lg:px-6 py-8">
      <Breadcrumb items={breadcrumbItems} />

      <div className="mb-6 mt-6">
        <h1 className="font-display text-2xl font-bold tracking-tight mb-1">
          Game Stores in {cityName}, {abbrev}
        </h1>
      </div>

      <StatsBar
        storeCount={result.total}
        activeCount={activeCount}
        wpnPremiumCount={premiumCount}
        onlineCount={onlineStores.length}
      />

      {cityDescription !== null && (
        <p className="text-zinc-400 text-sm leading-relaxed mb-6">
          {cityDescription}
        </p>
      )}

      <div className="mb-8">
        <h2 className="font-display text-lg font-semibold mb-4">
          All Stores in {cityName}
        </h2>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/30">
          <StoreTable stores={result.stores} enrichments={enrichments} />
        </div>

        <Suspense fallback={null}>
          <Pagination
            page={result.page}
            pageSize={result.pageSize}
            total={result.total}
          />
        </Suspense>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div>
          {storesWithCoords.length > 0 && (
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
          )}
        </div>
        <div>
          <OnlineStoresCard stores={onlineStores} />
        </div>
      </div>

      {nearbyCities.length > 0 && (
        <div className="mb-8">
          <NearbyCities stateSlug={stateSlug} cities={nearbyCities} />
        </div>
      )}

      <JsonLd data={jsonLdData} />
    </div>
  );
}
