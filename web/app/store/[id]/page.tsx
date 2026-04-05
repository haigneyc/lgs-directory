import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Breadcrumb } from "@/components/seo/breadcrumb";
import { JsonLd } from "@/components/seo/json-ld";
import { DetailMapLazy } from "@/components/map/detail-map-lazy";
import { getStore, getStoreEnrichment, getStoreContent, getStoreCategories, getOtherStoresInCity } from "@/lib/queries";
import { stateToSlug, cityToSlug, abbreviationToStateName } from "@/lib/slugs";
import { StoreStatusBadge, WpnBadge, OnlineSellerBadge } from "@/components/status-badge";
import { HoursBadge } from "@/components/hours-badge";
import { PresenceTable } from "@/components/presence-table";
import { formatAddress, formatDate, formatProduct, formatCategory } from "@/lib/format";
import { OtherCityStores } from "@/components/other-city-stores";
import { StoreFaq } from "@/components/seo/store-faq";
import { generateStoreFaq, buildFaqJsonLd } from "@/lib/faq";
import { Badge } from "@/components/ui/badge";
import {
  MapPin,
  Phone,
  Clock,
  Globe,
  Calendar,
  Star,
  ExternalLink,
  Tag,
} from "lucide-react";

/** Revalidate store detail pages every 24 hours -- data changes daily at most */
export const revalidate = 86400;

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const store = await getStore(id);

  if (!store) {
    return { title: "Store Not Found | Roll For Store" };
  }

  return {
    title: `${store.name} | Roll For Store`,
    description: `${store.name} in ${store.address.city}, ${store.address.state}. View hours, online presence, and WPN status.`,
  };
}

export default async function StoreDetailPage({ params }: PageProps) {
  const { id } = await params;
  const [store, enrichment, storeContent, categories] = await Promise.all([
    getStore(id),
    getStoreEnrichment(id),
    getStoreContent(id),
    getStoreCategories(id),
  ]);

  if (!store) {
    notFound();
  }

  console.assert(typeof store.name === "string", "StoreDetailPage: store.name must be a string");
  console.assert(typeof store.id === "string", "StoreDetailPage: store.id must be a string");

  const otherStores = await getOtherStoresInCity(
    store.id,
    store.address.state,
    store.address.city
  );
  const citySlug = cityToSlug(store.address.city);
  const stateSlugValue = stateToSlug(store.address.state);

  const faqItems = generateStoreFaq({ store, enrichment, storeContent });
  const rating = enrichment?.rating ?? 0;
  const hasRating = enrichment?.rating !== null && enrichment?.rating !== undefined;
  const hasReviews = hasRating && enrichment?.user_rating_count !== null && enrichment?.user_rating_count !== undefined;

  return (
    <div className="mx-auto max-w-7xl px-4 lg:px-6 py-8">
      <Breadcrumb
        items={[
          { name: "Home", href: "/" },
          { name: abbreviationToStateName(store.address.state) ?? store.address.state, href: `/stores/${stateToSlug(store.address.state)}` },
          { name: store.address.city, href: `/stores/${stateToSlug(store.address.state)}/${cityToSlug(store.address.city)}` },
          { name: store.name, href: `/store/${store.id}` },
        ]}
      />

      {/* Store Header */}
      <div className="mt-6 mb-8">
        <div className="flex flex-wrap items-start gap-4">
          <div className="flex-1 min-w-0">
            <h1 className="font-display text-3xl font-bold tracking-tight mb-2">
              {store.name}
            </h1>

            {/* Rating */}
            {hasRating && (
              <div className="flex items-center gap-2 mb-3">
                <div className="flex items-center gap-1">
                  <Star className="w-4 h-4 fill-yellow-500 text-yellow-500" />
                  <span className="font-display font-bold text-lg text-zinc-100">
                    {rating.toFixed(1)}
                  </span>
                </div>
                {hasReviews && (
                  <span className="text-sm text-zinc-500">
                    ({enrichment.user_rating_count} reviews)
                  </span>
                )}
              </div>
            )}

            {/* Address and phone */}
            <div className="space-y-1.5">
              <p className="flex items-center gap-2 text-zinc-400">
                <MapPin className="w-4 h-4 text-zinc-500 flex-shrink-0" />
                <span>{formatAddress(store.address)}</span>
              </p>
              {store.phone && (
                <p className="flex items-center gap-2 text-zinc-400">
                  <Phone className="w-4 h-4 text-zinc-500 flex-shrink-0" />
                  <a href={`tel:${store.phone}`} className="hover:text-zinc-200 transition-colors">
                    {store.phone}
                  </a>
                </p>
              )}
            </div>

            {/* Hours badge */}
            <div className="mt-3">
              <HoursBadge
                periods={enrichment?.hours_periods ?? null}
                weekdayText={enrichment?.hours_weekday_text ?? null}
                variant="detail"
              />
            </div>
          </div>

          {/* Status badges */}
          <div className="flex flex-wrap items-center gap-2 flex-shrink-0">
            <StoreStatusBadge status={store.status} />
            <WpnBadge level={store.wpn_level} />
            <OnlineSellerBadge sellsSingles={store.presences.some((p) => p.sells_mtg_singles === true)} />
          </div>
        </div>

        {/* Category badges */}
        {categories.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 mt-4">
            <Tag className="w-3.5 h-3.5 text-zinc-500" />
            {categories.map((cat) => (
              <Badge
                key={cat}
                variant="outline"
                className="bg-zinc-800/50 border-zinc-700/60 text-zinc-300 hover:bg-zinc-800 transition-colors"
              >
                {formatCategory(cat)}
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Left column -- main content */}
        <div className="lg:col-span-2 space-y-8">
          {/* Description */}
          {storeContent?.description && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
              <h2 className="font-display font-semibold text-zinc-200 mb-3">About</h2>
              <p className="text-zinc-400 text-sm leading-relaxed">
                {storeContent.description}
              </p>
            </div>
          )}

          {/* Products / Games */}
          {storeContent !== null && storeContent.products.length > 0 && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
              <h2 className="font-display font-semibold text-zinc-200 mb-3">Games & Products</h2>
              <div className="flex flex-wrap gap-2">
                {storeContent.products.map((product) => (
                  <Badge
                    key={product}
                    variant="secondary"
                    className="bg-zinc-800/80 text-zinc-300 border-zinc-700/50"
                  >
                    {formatProduct(product)}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Events */}
          {storeContent?.has_events && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
              <div className="flex items-center gap-2 mb-3">
                <Calendar className="w-4 h-4 text-yellow-500" />
                <h2 className="font-display font-semibold text-zinc-200">Events</h2>
              </div>
              {storeContent.event_url ? (
                <a
                  href={storeContent.event_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm text-yellow-500 hover:text-yellow-400 transition-colors"
                >
                  View Events Schedule
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              ) : (
                <p className="text-sm text-zinc-400">
                  This store hosts in-store events
                </p>
              )}
            </div>
          )}

          {/* Map */}
          {store.latitude && store.longitude && (
            <div className="rounded-xl border border-zinc-800 overflow-hidden">
              <div className="px-6 py-4 bg-zinc-900/50 border-b border-zinc-800">
                <div className="flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-yellow-500" />
                  <h2 className="font-display font-semibold text-zinc-200">Location</h2>
                </div>
              </div>
              <div className="h-72 bg-zinc-900">
                <DetailMapLazy
                  latitude={store.latitude}
                  longitude={store.longitude}
                  storeName={store.name}
                />
              </div>
            </div>
          )}

          {/* Online Presences */}
          <div className="rounded-xl border border-zinc-800 overflow-hidden">
            <div className="px-6 py-4 bg-zinc-900/50 border-b border-zinc-800">
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-yellow-500" />
                <h2 className="font-display font-semibold text-zinc-200">Online Presences</h2>
              </div>
            </div>
            <div className="bg-zinc-900/30">
              <PresenceTable presences={store.presences} />
            </div>
          </div>
        </div>

        {/* Right column -- sidebar */}
        <div className="space-y-6">
          {/* Store details card */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 space-y-5">
            <h3 className="font-display font-semibold text-sm text-zinc-300">Store Details</h3>

            <div className="space-y-4">
              <div>
                <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Discovery Source</p>
                <p className="text-sm font-mono text-zinc-300">{store.discovery_source}</p>
              </div>
              <div>
                <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">First Seen</p>
                <p className="text-sm text-zinc-300">{formatDate(store.first_seen)}</p>
              </div>
              <div>
                <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Last Validated</p>
                <p className="text-sm text-zinc-300">{formatDate(store.last_validated)}</p>
              </div>
            </div>
          </div>

          {/* Hours card */}
          {enrichment?.hours_weekday_text !== null && enrichment?.hours_weekday_text !== undefined && enrichment.hours_weekday_text.length > 0 && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
              <div className="flex items-center gap-2 mb-4">
                <Clock className="w-4 h-4 text-yellow-500" />
                <h3 className="font-display font-semibold text-sm text-zinc-300">Hours</h3>
              </div>
              <ul className="space-y-1.5">
                {enrichment.hours_weekday_text.map((line) => (
                  <li key={line} className="text-sm text-zinc-400 flex items-start">
                    <span className="inline-block w-1 h-1 rounded-full bg-zinc-600 mt-2 mr-2 flex-shrink-0" />
                    {line}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Google Maps link */}
          {enrichment?.photo_refs !== null && enrichment?.photo_refs !== undefined && enrichment.photo_refs.length > 0 && store.google_place_id && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6">
              <a
                href={`https://www.google.com/maps/place/?q=place_id:${store.google_place_id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm text-yellow-500 hover:text-yellow-400 transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                View on Google Maps
              </a>
            </div>
          )}
        </div>
      </div>

      {/* FAQ Section */}
      {faqItems.length > 0 && (
        <div className="border-t border-zinc-800/60 pt-10 mb-8">
          <StoreFaq items={faqItems} storeName={store.name} />
        </div>
      )}

      {/* Other Stores in City */}
      {otherStores.length > 0 && (
        <OtherCityStores
          stores={otherStores}
          cityName={store.address.city}
          stateSlug={stateSlugValue}
          citySlug={citySlug}
        />
      )}

      {/* Browse links */}
      <div className="border-t border-zinc-800/60 pt-8 mb-8">
        <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Browse More</h2>
        <div className="flex flex-wrap gap-3">
          <a
            href={`/stores/${stateSlugValue}/${citySlug}`}
            className="rounded-md bg-zinc-800 px-3 py-1.5 text-sm text-zinc-400 hover:bg-zinc-700 transition-colors"
          >
            All stores in {store.address.city}
          </a>
          <a
            href={`/stores/${stateSlugValue}`}
            className="rounded-md bg-zinc-800 px-3 py-1.5 text-sm text-zinc-400 hover:bg-zinc-700 transition-colors"
          >
            All stores in {abbreviationToStateName(store.address.state) ?? store.address.state}
          </a>
        </div>
      </div>

      {/* Notes */}
      {store.notes && (
        <div className="border-t border-zinc-800/60 pt-8 mb-8">
          <h2 className="font-display font-semibold text-zinc-200 mb-3">Notes</h2>
          <p className="text-zinc-400 text-sm whitespace-pre-wrap">{store.notes}</p>
        </div>
      )}

      <JsonLd data={buildLocalBusinessJsonLd(store, enrichment)} />
      {faqItems.length > 0 && <JsonLd data={buildFaqJsonLd(faqItems)} />}
    </div>
  );
}

/** Schema.org day names indexed by Google Places day number (0=Sunday). */
const SCHEMA_DAY_NAMES = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
] as const;

function buildLocalBusinessJsonLd(
  store: Awaited<ReturnType<typeof getStore>> & object,
  enrichment: Awaited<ReturnType<typeof getStoreEnrichment>>
): Record<string, unknown> {
  console.assert(store !== null, "buildLocalBusinessJsonLd: store must not be null");
  console.assert(typeof store.name === "string", "buildLocalBusinessJsonLd: store.name must be a string");

  const websitePresence = store.presences.find(
    (p) => p.channel_type === "website" && p.status === "active"
  );

  const data: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    name: store.name,
    address: {
      "@type": "PostalAddress",
      streetAddress: store.address.street,
      addressLocality: store.address.city,
      addressRegion: store.address.state,
      postalCode: store.address.zip_code,
    },
  };

  if (store.phone) {
    data.telephone = store.phone;
  }

  if (store.latitude !== null && store.longitude !== null) {
    data.geo = {
      "@type": "GeoCoordinates",
      latitude: store.latitude,
      longitude: store.longitude,
    };
  }

  if (websitePresence) {
    data.url = websitePresence.url;
  }

  // Add OpeningHoursSpecification from periods data
  if (enrichment?.hours_periods !== null && enrichment?.hours_periods !== undefined && enrichment.hours_periods.length > 0) {
    const specs: Record<string, unknown>[] = [];
    const limit = Math.min(enrichment.hours_periods.length, 14);
    for (let i = 0; i < limit; i++) {
      const period = enrichment.hours_periods[i];
      if (period.open.day < 0 || period.open.day > 6) {
        continue;
      }
      const dayName = SCHEMA_DAY_NAMES[period.open.day];
      const opens = `${period.open.hour.toString().padStart(2, "0")}:${period.open.minute.toString().padStart(2, "0")}`;
      const closes = `${period.close.hour.toString().padStart(2, "0")}:${period.close.minute.toString().padStart(2, "0")}`;
      specs.push({
        "@type": "OpeningHoursSpecification",
        dayOfWeek: dayName,
        opens,
        closes,
      });
    }
    data.openingHoursSpecification = specs;
  }

  // Add aggregate rating
  if (enrichment?.rating !== null && enrichment?.rating !== undefined && enrichment?.user_rating_count !== null && enrichment?.user_rating_count !== undefined) {
    data.aggregateRating = {
      "@type": "AggregateRating",
      ratingValue: enrichment.rating,
      reviewCount: enrichment.user_rating_count,
    };
  }

  return data;
}
