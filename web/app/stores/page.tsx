import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { MapPin } from "lucide-react";
import { getStateIndex } from "@/lib/queries";
import { Breadcrumb } from "@/components/seo/breadcrumb";
import { JsonLd } from "@/components/seo/json-ld";
import { SITE_URL } from "@/lib/site";

export const metadata: Metadata = {
  title: "Game Stores by State | Roll For Store",
  description:
    "Browse local game stores across the United States. Find WPN-certified stores, comic shops, retro game stores, and Warhammer hobby shops by state.",
  alternates: { canonical: `${SITE_URL}/stores` },
  openGraph: {
    title: "Game Stores by State | Roll For Store",
    description:
      "Browse local game stores across the United States by state.",
    type: "website",
    url: `${SITE_URL}/stores`,
    siteName: "Roll For Store",
  },
};

/**
 * Synchronous shell — MUST NOT await anything (PERF-026). Forwards to
 * an async child under Suspense, matching the `stores/[state]/page.tsx`
 * pattern so Cache Components can prerender the static chrome.
 */
export default function StoresIndexPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 lg:px-6 py-8">
      <Breadcrumb
        items={[
          { name: "Home", href: "/" },
          { name: "States", href: "/stores" },
        ]}
      />
      <div className="mb-8 mt-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-yellow-600/10 text-yellow-500">
            <MapPin className="w-5 h-5" />
          </div>
          <h1 className="font-display text-2xl font-bold tracking-tight">
            Game Stores by State
          </h1>
        </div>
        <p className="text-sm text-zinc-500 max-w-2xl">
          Browse local game stores, comic shops, and hobby stores across all
          US states. Click a state to see every store we track there.
        </p>
      </div>

      <Suspense fallback={<StatesGridSkeleton />}>
        <StatesGrid />
      </Suspense>
    </div>
  );
}

function StatesGridSkeleton() {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-6">
      <p className="text-sm text-zinc-500">Loading states…</p>
    </div>
  );
}

async function StatesGrid() {
  const states = await getStateIndex();
  console.assert(Array.isArray(states), "StatesGrid: states must be an array");
  console.assert(states.length >= 0, "StatesGrid: states length must be non-negative");

  const sorted = [...states].sort((a, b) => a.state.localeCompare(b.state));

  const itemListElements: Record<string, unknown>[] = [];
  const limit = Math.min(sorted.length, 60);
  for (let i = 0; i < limit; i++) {
    const s = sorted[i];
    itemListElements.push({
      "@type": "ListItem",
      position: i + 1,
      url: `${SITE_URL}/stores/${s.slug}`,
      name: s.state,
    });
  }

  const jsonLdData: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: "Game Stores by State",
    numberOfItems: sorted.length,
    itemListElement: itemListElements,
  };

  return (
    <>
      <JsonLd data={jsonLdData} />
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {sorted.map((s) => (
          <Link
            key={s.slug}
            href={`/stores/${s.slug}`}
            className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3 hover:border-zinc-700 hover:bg-zinc-900 transition-colors"
          >
            <span className="font-medium text-zinc-100">{s.state}</span>
            <span className="text-sm text-zinc-500 font-mono">
              {s.store_count}
            </span>
          </Link>
        ))}
      </div>
    </>
  );
}
