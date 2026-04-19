import type { Metadata } from "next";
import { Suspense } from "react";
import { headers } from "next/headers";
import Link from "next/link";
import { MapPin } from "lucide-react";
import NearMeClient from "./near-me-client";
import { getNearbyStores } from "@/lib/queries";
import { JsonLd } from "@/components/seo/json-ld";
import { Breadcrumb } from "@/components/seo/breadcrumb";
import { AffiliateDisclosure } from "@/components/affiliate-disclosure";
import { AmazonShelf } from "@/components/amazon/amazon-shelf";
import { AffiliateLink } from "@/components/affiliate-link";
import { SHELVES } from "@/lib/amazon-shelves";
import { SITE_URL, EBAY_URLS } from "@/lib/site";
import { formatCityState, formatDistance } from "@/lib/format";
import { storeHref } from "@/lib/slugs";
import { toDisplayCase } from "@/lib/display-case";

/**
 * `/near-me` — server-rendered nearest-store list using Vercel's edge
 * geo headers as the initial coordinates, with a client component that
 * progressively enhances the UX once the user grants precise browser
 * geolocation.
 *
 * The server shell is per-request dynamic (reads request headers) and
 * MUST NOT be wrapped in `use cache`. The static chrome prerenders, the
 * store list streams in via a Suspense boundary.
 */

export const metadata: Metadata = {
  title: "Tabletop Gaming Stores Near Me | Roll For Store",
  description:
    "Find tabletop gaming stores, TCG stores, and miniatures shops near you. Browse local game stores by distance with hours, phone, and directions.",
  alternates: { canonical: `${SITE_URL}/near-me` },
  openGraph: {
    title: "Tabletop Gaming Stores Near Me | Roll For Store",
    description:
      "Find tabletop gaming stores, TCG stores, and miniatures shops near you.",
    type: "website",
    url: `${SITE_URL}/near-me`,
    siteName: "Roll For Store",
  },
};

// US geographic center — fallback when edge headers are missing (local
// dev, non-Vercel environments, bots without geo). The list this
// produces is still useful generic content for crawlers.
const FALLBACK_LAT = 39.8283;
const FALLBACK_LNG = -98.5795;
const DEFAULT_RADIUS_MILES = 50;
const DEFAULT_LIMIT = 25;

interface InitialGeo {
  lat: number;
  lng: number;
  city: string | null;
  state: string | null;
  fromHeaders: boolean;
}

/**
 * Safely decode a Vercel geo header. Vercel URL-encodes non-ASCII
 * values (e.g. "São Paulo" -> "S%C3%A3o%20Paulo"), but a malformed or
 * corrupted header (e.g. "%GG") would cause `decodeURIComponent` to
 * throw `URIError: URI malformed` and crash the render. Fall back to
 * the raw header in that case.
 */
function safeDecodeHeader(raw: string | null): string | null {
  if (raw === null) return null;
  console.assert(typeof raw === "string", "safeDecodeHeader: raw must be a string or null");
  console.assert(raw.length < 1000, "safeDecodeHeader: raw length sanity");
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

async function readInitialGeo(): Promise<InitialGeo> {
  const h = await headers();
  const latRaw = h.get("x-vercel-ip-latitude");
  const lngRaw = h.get("x-vercel-ip-longitude");
  const cityRaw = h.get("x-vercel-ip-city");
  const stateRaw = h.get("x-vercel-ip-country-region");

  const lat = latRaw !== null ? Number.parseFloat(latRaw) : NaN;
  const lng = lngRaw !== null ? Number.parseFloat(lngRaw) : NaN;
  const hasCoords =
    Number.isFinite(lat) &&
    Number.isFinite(lng) &&
    lat >= -90 &&
    lat <= 90 &&
    lng >= -180 &&
    lng <= 180;

  console.assert(
    !hasCoords || (lat >= -90 && lat <= 90),
    "readInitialGeo: lat out of range"
  );
  console.assert(
    !hasCoords || (lng >= -180 && lng <= 180),
    "readInitialGeo: lng out of range"
  );

  return {
    lat: hasCoords ? lat : FALLBACK_LAT,
    lng: hasCoords ? lng : FALLBACK_LNG,
    city: safeDecodeHeader(cityRaw),
    state: stateRaw,
    fromHeaders: hasCoords,
  };
}

export default function NearMePage() {
  return (
    <div className="mx-auto max-w-7xl px-4 lg:px-6 py-8">
      <Breadcrumb
        items={[
          { name: "Home", href: "/" },
          { name: "Near Me", href: "/near-me" },
        ]}
      />
      <div className="mb-6 mt-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-yellow-600/10 text-yellow-500">
            <MapPin className="w-5 h-5" />
          </div>
          <h1 className="font-display text-2xl font-bold tracking-tight">
            Tabletop Gaming Stores Near Me
          </h1>
        </div>
        <p className="text-sm text-zinc-500 max-w-2xl">
          The nearest local game stores based on your approximate location.
          Use the search below to refine by city, zip code, or your precise
          browser location.
        </p>
        <p className="text-sm text-zinc-500 max-w-2xl mt-2">
          Whether you&apos;re hunting for a tabletop game store stocked with
          the latest releases, a TCG store running Friday Night Magic, or a
          miniatures shop with Warhammer and painting supplies — Roll For Store
          shows you every tabletop gaming destination in your area.
        </p>
      </div>

      <Suspense fallback={<NearbySkeleton />}>
        <NearbyStoresList />
      </Suspense>
    </div>
  );
}

function NearbySkeleton() {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-6">
      <p className="text-sm text-zinc-500">Loading nearest stores…</p>
    </div>
  );
}

async function NearbyStoresList() {
  const geo = await readInitialGeo();
  console.assert(Number.isFinite(geo.lat), "NearbyStoresList: geo.lat must be finite");
  console.assert(Number.isFinite(geo.lng), "NearbyStoresList: geo.lng must be finite");

  const stores = await getNearbyStores(
    geo.lat,
    geo.lng,
    DEFAULT_RADIUS_MILES,
    DEFAULT_LIMIT
  );

  console.assert(Array.isArray(stores), "NearbyStoresList: stores must be an array");

  const itemListElements: Record<string, unknown>[] = [];
  const jsonLdLimit = Math.min(stores.length, DEFAULT_LIMIT);
  for (let i = 0; i < jsonLdLimit; i++) {
    const store = stores[i];
    itemListElements.push({
      "@type": "ListItem",
      position: i + 1,
      url: `${SITE_URL}${storeHref(store)}`,
      name: toDisplayCase(store.name),
    });
  }
  const jsonLdData: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: "Game Stores Near Me",
    numberOfItems: itemListElements.length,
    itemListElement: itemListElements,
  };

  return (
    <>
      <JsonLd data={jsonLdData} />

      <section className="mb-6 rounded-xl border border-yellow-600/25 bg-yellow-600/5 p-4 sm:p-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <h2 className="font-display text-base font-semibold text-yellow-300">
              Shop TCG Singles on eBay
            </h2>
            <p className="text-sm text-zinc-500">
              Sealed product, graded cards, and collectible singles for the games most people search for nearby.
            </p>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <AffiliateLink
            href={EBAY_URLS.collections.mtg}
            network="ebay"
            placement="near-me-top-cta"
            className="group rounded-lg border border-yellow-600/30 bg-zinc-950/40 px-4 py-3 transition-colors hover:border-yellow-500/50 hover:bg-yellow-600/10"
          >
            <p className="text-sm font-medium text-zinc-100 transition-colors group-hover:text-yellow-300">
              Shop MTG Singles on eBay
            </p>
            <p className="mt-1 text-xs text-zinc-500">
              Browse booster boxes, graded staples, and collectible Magic cards.
            </p>
          </AffiliateLink>
          <AffiliateLink
            href={EBAY_URLS.collections.pokemon}
            network="ebay"
            placement="near-me-top-cta"
            className="group rounded-lg border border-yellow-600/30 bg-zinc-950/40 px-4 py-3 transition-colors hover:border-yellow-500/50 hover:bg-yellow-600/10"
          >
            <p className="text-sm font-medium text-zinc-100 transition-colors group-hover:text-yellow-300">
              Shop Pokemon Cards on eBay
            </p>
            <p className="mt-1 text-xs text-zinc-500">
              Find sealed product, slabs, and high-demand singles from recent and vintage sets.
            </p>
          </AffiliateLink>
        </div>
        <AffiliateDisclosure className="mt-2" />
      </section>

      {geo.fromHeaders && geo.city !== null && (
        <p className="text-xs text-zinc-500 mb-4">
          Showing stores near{" "}
          <span className="text-zinc-300">
            {toDisplayCase(geo.city)}
            {geo.state !== null ? `, ${geo.state}` : ""}
          </span>
          . Use your precise location below for a tighter radius.
        </p>
      )}

      {stores.length === 0 ? (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-6 text-sm text-zinc-500">
          No stores found within {DEFAULT_RADIUS_MILES} miles. Try searching
          by city or zip code below.
        </div>
      ) : (
        <ul className="divide-y divide-zinc-800 rounded-lg border border-zinc-800 bg-zinc-900/40 mb-8">
          {stores.map((store) => (
            <li key={store.id}>
              <Link
                href={storeHref(store)}
                className="flex items-center justify-between px-4 py-3 hover:bg-zinc-900 transition-colors"
              >
                <div className="min-w-0">
                  <p className="font-medium text-sm text-zinc-100 truncate">
                    {toDisplayCase(store.name)}
                  </p>
                  <p className="text-xs text-zinc-500 mt-0.5">
                    {formatCityState(store.address)}
                  </p>
                </div>
                <span className="text-xs font-mono text-zinc-400 flex-shrink-0">
                  {formatDistance(store.distance_miles)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <div className="mb-8">
        <AmazonShelf
          shelf={SHELVES["tcg-essentials"]}
          placement="near-me-bottom-shelf"
        />
      </div>

      <NearMeClient
        initialLat={geo.fromHeaders ? geo.lat : null}
        initialLng={geo.fromHeaders ? geo.lng : null}
        initialCity={geo.city}
        initialState={geo.state}
      />
    </>
  );
}
