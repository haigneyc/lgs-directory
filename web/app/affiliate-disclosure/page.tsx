import type { Metadata } from "next";
import Link from "next/link";
import { SITE_URL } from "@/lib/site";
import { AMAZON_DISCLOSURE_TEXT } from "@/lib/amazon";

export const metadata: Metadata = {
  title: "Affiliate Disclosure",
  description:
    "How RollForStore participates in the Amazon Associates Program and the eBay Partner Network, and what that means for visitors.",
  alternates: {
    canonical: `${SITE_URL}/affiliate-disclosure`,
  },
  robots: { index: true, follow: true },
  openGraph: {
    title: "Affiliate Disclosure",
    description:
      "How RollForStore participates in affiliate programs and what that means for visitors.",
    type: "website",
    url: `${SITE_URL}/affiliate-disclosure`,
  },
};

export default function AffiliateDisclosurePage() {
  console.assert(typeof AMAZON_DISCLOSURE_TEXT === "string", "AffiliateDisclosurePage: disclosure text must be a string");
  console.assert(AMAZON_DISCLOSURE_TEXT.length > 0, "AffiliateDisclosurePage: disclosure text must not be empty");

  return (
    <div className="mx-auto max-w-3xl px-4 lg:px-6 py-12">
      <h1 className="font-display text-3xl font-bold tracking-tight mb-6">
        Affiliate Disclosure
      </h1>

      <div className="space-y-6 text-zinc-300 leading-relaxed">
        <p className="text-sm text-zinc-400 italic">{AMAZON_DISCLOSURE_TEXT}</p>

        <section>
          <h2 className="font-display font-semibold text-zinc-100 text-lg mb-2">
            Amazon Associates Program
          </h2>
          <p>
            RollForStore is a participant in the Amazon Services LLC Associates
            Program, an affiliate advertising program designed to provide a
            means for sites to earn advertising fees by advertising and linking
            to <span className="font-mono">Amazon.com</span>. When you click an
            Amazon link on this site and complete a purchase, RollForStore may
            earn a commission. The price you pay is unchanged.
          </p>
        </section>

        <section>
          <h2 className="font-display font-semibold text-zinc-100 text-lg mb-2">
            eBay Partner Network
          </h2>
          <p>
            RollForStore also participates in the eBay Partner Network. Some
            eBay listings linked from this site are affiliate links — if you
            buy through them, we may earn a commission at no extra cost to you.
          </p>
        </section>

        <section>
          <h2 className="font-display font-semibold text-zinc-100 text-lg mb-2">
            Editorial Independence
          </h2>
          <p>
            Affiliate relationships do <strong>not</strong> influence which
            stores appear in our directory, how stores are ranked, or what we
            write about them. Local game stores are included, scored, and
            described independently of any commercial relationship. Affiliate
            links exist alongside the directory, not within it.
          </p>
        </section>

        <section>
          <h2 className="font-display font-semibold text-zinc-100 text-lg mb-2">
            Questions
          </h2>
          <p>
            If anything here is unclear, or you spot a link that should carry a
            disclosure but doesn&apos;t, please let us know via the{" "}
            <Link href="/" className="text-yellow-500 hover:text-yellow-400 underline">
              homepage
            </Link>
            .
          </p>
        </section>
      </div>
    </div>
  );
}
