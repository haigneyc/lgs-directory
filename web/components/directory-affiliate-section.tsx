import { AmazonShelf } from "@/components/amazon/amazon-shelf";
import { AffiliateDisclosure } from "@/components/affiliate-disclosure";
import { AffiliateLink } from "@/components/affiliate-link";
import { SHELVES } from "@/lib/amazon-shelves";
import { EBAY_URLS } from "@/lib/site";

interface DirectoryAffiliateSectionProps {
  placementBase: "state-directory" | "city-directory";
}

export function DirectoryAffiliateSection({
  placementBase,
}: Readonly<DirectoryAffiliateSectionProps>) {
  console.assert(
    placementBase === "state-directory" || placementBase === "city-directory",
    "DirectoryAffiliateSection: placementBase must be a supported directory placement",
  );
  console.assert(
    SHELVES["tcg-essentials"].links.length >= 4,
    "DirectoryAffiliateSection: tcg shelf must expose enough links for the strip variant",
  );

  const ebayPlacement = `${placementBase}-ebay-strip`;
  const amazonPlacement = `${placementBase}-shelf`;

  return (
    <div className="mb-8 space-y-4">
      <section className="rounded-xl border border-yellow-600/25 bg-yellow-600/5 p-4 sm:p-5">
        <div className="mb-3">
          <h2 className="font-display text-base font-semibold text-yellow-300">
            Shop TCG Singles on eBay
          </h2>
          <p className="text-sm text-zinc-500">
            Add sleeves, sealed product, and collectible singles while you browse nearby stores.
          </p>
        </div>

        <div className="grid gap-2.5 sm:grid-cols-2">
          <AffiliateLink
            href={EBAY_URLS.collections.mtg}
            network="ebay"
            placement={ebayPlacement}
            className="group rounded-lg border border-yellow-600/30 bg-zinc-950/40 px-3.5 py-3 transition-colors hover:border-yellow-500/50 hover:bg-yellow-600/10"
          >
            <p className="text-sm font-medium text-zinc-100 transition-colors group-hover:text-yellow-300">
              Shop MTG Singles on eBay
            </p>
            <p className="mt-1 text-xs text-zinc-500">
              Booster boxes, graded staples, and collectible Magic cards.
            </p>
          </AffiliateLink>

          <AffiliateLink
            href={EBAY_URLS.collections.pokemon}
            network="ebay"
            placement={ebayPlacement}
            className="group rounded-lg border border-yellow-600/30 bg-zinc-950/40 px-3.5 py-3 transition-colors hover:border-yellow-500/50 hover:bg-yellow-600/10"
          >
            <p className="text-sm font-medium text-zinc-100 transition-colors group-hover:text-yellow-300">
              Shop Pokemon Cards on eBay
            </p>
            <p className="mt-1 text-xs text-zinc-500">
              Sealed product, slabs, and high-demand singles from recent and vintage sets.
            </p>
          </AffiliateLink>
        </div>

        <AffiliateDisclosure className="mt-2" />
      </section>

      <AmazonShelf
        shelf={SHELVES["tcg-essentials"]}
        placement={amazonPlacement}
        variant="strip"
      />
    </div>
  );
}
