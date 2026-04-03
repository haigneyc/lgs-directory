import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Breadcrumb } from "@/components/seo/breadcrumb";
import { JsonLd } from "@/components/seo/json-ld";
import { DetailMapLazy } from "@/components/map/detail-map-lazy";
import { getStore, getStoreEnrichment, getStoreContent } from "@/lib/queries";
import { stateToSlug, cityToSlug, abbreviationToStateName } from "@/lib/slugs";
import { StoreStatusBadge, WpnBadge } from "@/components/status-badge";
import { PresenceTable } from "@/components/presence-table";
import { formatAddress, formatDate, formatProduct } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

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
  const [store, enrichment, storeContent] = await Promise.all([
    getStore(id),
    getStoreEnrichment(id),
    getStoreContent(id),
  ]);

  if (!store) {
    notFound();
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <Breadcrumb
        items={[
          { name: "Home", href: "/" },
          { name: abbreviationToStateName(store.address.state) ?? store.address.state, href: `/stores/${stateToSlug(store.address.state)}` },
          { name: store.address.city, href: `/stores/${stateToSlug(store.address.state)}/${cityToSlug(store.address.city)}` },
          { name: store.name, href: `/store/${store.id}` },
        ]}
      />

      <div className="flex flex-wrap items-start gap-4 mb-6">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl font-semibold tracking-tight">
              {store.name}
            </h1>
            {enrichment?.rating !== null && enrichment?.rating !== undefined && enrichment?.user_rating_count !== null && enrichment?.user_rating_count !== undefined && (
              <span className="text-sm whitespace-nowrap">
                <span className="text-amber-400">{"\u2605"}</span>{" "}
                <span className="text-zinc-300">{enrichment.rating.toFixed(1)}</span>{" "}
                <span className="text-zinc-500">({enrichment.user_rating_count} reviews)</span>
              </span>
            )}
          </div>
          <p className="text-zinc-400">{formatAddress(store.address)}</p>
          {store.phone && (
            <p className="text-zinc-500 text-sm mt-1">{store.phone}</p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <StoreStatusBadge status={store.status} />
          <WpnBadge level={store.wpn_level} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-zinc-500 font-normal uppercase tracking-wider">
              Discovery Source
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm font-mono text-zinc-300">
              {store.discovery_source}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-zinc-500 font-normal uppercase tracking-wider">
              First Seen
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-zinc-300">
              {formatDate(store.first_seen)}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-zinc-500 font-normal uppercase tracking-wider">
              Last Validated
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-zinc-300">
              {formatDate(store.last_validated)}
            </p>
          </CardContent>
        </Card>
      </div>

      {storeContent?.description && (
        <div className="mb-8">
          <p className="text-zinc-400 text-sm leading-relaxed">
            {storeContent.description}
          </p>
        </div>
      )}

      {storeContent !== null && storeContent.products.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-2">
            Games &amp; Products
          </h2>
          <div className="flex flex-wrap gap-2">
            {storeContent.products.map((product) => (
              <Badge key={product} variant="secondary">
                {formatProduct(product)}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {storeContent?.has_events && (
        <div className="mb-8">
          <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-2">
            Events
          </h2>
          {storeContent.event_url ? (
            <a
              href={storeContent.event_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
            >
              View Events Schedule
            </a>
          ) : (
            <p className="text-sm text-zinc-400">
              This store hosts in-store events
            </p>
          )}
        </div>
      )}

      {store.latitude && store.longitude && (
        <div className="mb-8">
          <h2 className="text-lg font-medium mb-3">Location</h2>
          <div className="rounded-lg border border-zinc-800 overflow-hidden h-64 bg-zinc-900">
            <DetailMapLazy
              latitude={store.latitude}
              longitude={store.longitude}
              storeName={store.name}
            />
          </div>
        </div>
      )}

      {enrichment?.hours_weekday_text !== null && enrichment?.hours_weekday_text !== undefined && enrichment.hours_weekday_text.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-2">Hours</h2>
          <ul className="space-y-1">
            {enrichment.hours_weekday_text.map((line) => (
              <li key={line} className="text-sm text-zinc-400">{line}</li>
            ))}
          </ul>
        </div>
      )}

      {enrichment?.photo_refs !== null && enrichment?.photo_refs !== undefined && enrichment.photo_refs.length > 0 && store.google_place_id && (
        <div className="mb-8">
          <a
            href={`https://www.google.com/maps/place/?q=place_id:${store.google_place_id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            View on Google Maps
          </a>
        </div>
      )}

      <Separator className="bg-zinc-800 mb-8" />

      <div>
        <h2 className="text-lg font-medium mb-3">Online Presences</h2>
        <div className="rounded-lg border border-zinc-800 bg-zinc-950">
          <PresenceTable presences={store.presences} />
        </div>
      </div>

      {store.notes && (
        <>
          <Separator className="bg-zinc-800 my-8" />
          <div>
            <h2 className="text-lg font-medium mb-2">Notes</h2>
            <p className="text-zinc-400 text-sm whitespace-pre-wrap">
              {store.notes}
            </p>
          </div>
        </>
      )}

      <JsonLd data={buildLocalBusinessJsonLd(store)} />
    </div>
  );
}

function buildLocalBusinessJsonLd(
  store: Awaited<ReturnType<typeof getStore>> & object
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

  return data;
}
