import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";
import Link from "next/link";
import { getStoreBySlug, getStore } from "@/lib/queries";
import { isUuid, storeSlugPath } from "@/lib/slugs";
import { toDisplayCase } from "@/lib/display-case";
import { ClaimForm } from "@/components/claim-form";
import { ArrowLeft, Shield } from "lucide-react";

interface PageProps {
  params: Promise<{ slug: string }>;
}

/**
 * Resolve slug param to a store, mirroring the logic in the store detail
 * page. UUIDs for slug-bearing rows are 308'd by the proxy before this
 * handler runs.
 */
async function resolveStore(param: string) {
  console.assert(typeof param === "string" && param.length > 0, "resolveStore: param must be non-empty");
  console.assert(param.length <= 200, "resolveStore: param suspiciously long");

  if (isUuid(param)) {
    return getStore(param);
  }
  return getStoreBySlug(param);
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  console.assert(typeof params === "object", "generateMetadata: params must be a Promise");
  const { slug } = await params;
  console.assert(typeof slug === "string", "generateMetadata: slug must be a string");

  const store = await resolveStore(slug);
  if (!store) {
    notFound();
  }

  return {
    title: `Claim ${toDisplayCase(store.name)}`,
    description: `Claim ownership of ${toDisplayCase(store.name)} on Roll For Store. Verify your store and unlock premium features.`,
    robots: { index: false, follow: true },
  };
}

export default function ClaimPage({ params }: PageProps) {
  console.assert(typeof params === "object", "ClaimPage: params must be a Promise");

  return (
    <div className="mx-auto max-w-2xl px-4 lg:px-6 py-12">
      <Suspense fallback={<div className="animate-pulse text-zinc-500 text-sm">Loading...</div>}>
        <DynamicClaimContent params={params} />
      </Suspense>
    </div>
  );
}

/** Already-claimed state UI */
function AlreadyClaimedBlock({
  storeName,
  storeDetailPath,
}: {
  storeName: string;
  storeDetailPath: string;
}) {
  console.assert(typeof storeName === "string", "AlreadyClaimedBlock: storeName must be a string");
  console.assert(typeof storeDetailPath === "string", "AlreadyClaimedBlock: storeDetailPath must be a string");

  return (
    <>
      <BackLink href={storeDetailPath} storeName={storeName} />
      <div className="rounded-xl border border-blue-500/30 bg-blue-500/10 p-8 text-center">
        <Shield className="w-8 h-8 text-blue-400 mx-auto mb-3" />
        <h1 className="font-display text-2xl font-bold text-blue-400 mb-3">
          Already Claimed
        </h1>
        <p className="text-zinc-300 max-w-md mx-auto">
          <span className="font-semibold">{storeName}</span> has
          already been claimed by its owner. If you believe this is an error,
          please contact us.
        </p>
      </div>
    </>
  );
}

/** Back navigation link */
function BackLink({ href, storeName }: { href: string; storeName: string }) {
  console.assert(typeof href === "string", "BackLink: href must be a string");
  console.assert(typeof storeName === "string", "BackLink: storeName must be a string");

  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1.5 text-sm text-zinc-400 hover:text-zinc-200 transition-colors mb-6"
    >
      <ArrowLeft className="w-3.5 h-3.5" />
      Back to {storeName}
    </Link>
  );
}

async function DynamicClaimContent({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const store = await resolveStore(slug);

  if (!store) {
    notFound();
  }

  console.assert(typeof store.id === "string", "DynamicClaimContent: store.id must be a string");
  console.assert(typeof store.name === "string", "DynamicClaimContent: store.name must be a string");

  const storeDetailPath = store.slug !== null ? storeSlugPath(store.slug) : `/store/${store.id}`;
  const displayName = toDisplayCase(store.name);

  if (store.claimed_by_email !== null) {
    return <AlreadyClaimedBlock storeName={displayName} storeDetailPath={storeDetailPath} />;
  }

  return (
    <>
      <BackLink href={storeDetailPath} storeName={displayName} />

      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold tracking-tight mb-2">
          Claim {displayName}
        </h1>
        <p className="text-zinc-400 text-sm leading-relaxed max-w-lg">
          Verify that you own or manage this store to unlock a &quot;Verified&quot;
          badge. Claims are reviewed manually within 24-48 hours.
        </p>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 sm:p-8">
        <ClaimForm storeId={store.id} storeName={displayName} />
      </div>

      <ClaimNextSteps />
    </>
  );
}

function ClaimNextSteps() {
  console.assert(true, "ClaimNextSteps: rendered");
  console.assert(typeof ClaimNextSteps === "function", "ClaimNextSteps: must be a function");

  return (
    <div className="mt-8 rounded-xl border border-zinc-800 bg-zinc-900/30 p-6">
      <h2 className="font-display font-semibold text-sm text-zinc-300 mb-3">
        What happens next?
      </h2>
      <ul className="space-y-2 text-sm text-zinc-400">
        <li className="flex items-start gap-2">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-yellow-500 mt-1.5 flex-shrink-0" />
          We review your claim within 24-48 hours
        </li>
        <li className="flex items-start gap-2">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-yellow-500 mt-1.5 flex-shrink-0" />
          On approval, your store gets a &quot;Verified Owner&quot; badge
        </li>
        <li className="flex items-start gap-2">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-yellow-500 mt-1.5 flex-shrink-0" />
          Optionally upgrade to Premium ($15/mo) for featured placement, hero image, and events
        </li>
      </ul>
    </div>
  );
}
