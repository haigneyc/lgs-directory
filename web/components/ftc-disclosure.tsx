/**
 * FTC / Amazon-Creator-Connections mandatory disclosure.
 *
 * Rendered above the fold on any affiliate-bearing page (currently:
 * every ``/guides/[slug]`` post that declares a ``disclosure`` in its
 * frontmatter). Per Amazon Creator Connections Program Policies
 * section 1.3 the disclosure must be "clear and conspicuous" — a muted
 * footnote does not qualify. Styling is intentionally high-contrast.
 *
 * Disclosure copy matches Amazon's published templates:
 *   - ``amazon-creator-connections`` → campaign-specific creator copy
 *   - ``amazon-associates``         → existing Amazon Associates boilerplate
 *
 * Keep this component server-renderable (no ``"use client"``) so it lands
 * in the prerendered shell and does not block LCP.
 */

const DISCLOSURE_COPY = {
  "amazon-creator-connections":
    "This post is part of an Amazon Creator Connections campaign. I receive compensation for recommending products and may earn commissions on qualifying purchases. Opinions are my own.",
  "amazon-associates":
    "As an Amazon Associate, RollForStore earns from qualifying purchases. Some links on this page are affiliate links — the price you pay is unchanged.",
  "ebay-partner-network":
    "RollForStore participates in the eBay Partner Network. Some links on this page are affiliate links — if you buy through them, we may earn a commission at no extra cost to you.",
} as const;

export type FTCDisclosureCampaign = keyof typeof DISCLOSURE_COPY;

const VARIANTS = ["banner", "inline"] as const;
export type FTCDisclosureVariant = (typeof VARIANTS)[number];

interface FTCDisclosureProps {
  campaign: FTCDisclosureCampaign;
  variant?: FTCDisclosureVariant;
}

const BANNER_CLASSES =
  "not-prose mb-6 rounded-lg border border-yellow-500/50 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-100";
const INLINE_CLASSES =
  "not-prose my-4 rounded-md border-l-4 border-yellow-500 bg-yellow-500/5 px-4 py-3 text-sm text-yellow-100";

const DISCLOSURE_LABEL = "Disclosure";

export function FTCDisclosure({
  campaign,
  variant = "banner",
}: FTCDisclosureProps) {
  console.assert(
    typeof campaign === "string" && campaign in DISCLOSURE_COPY,
    "FTCDisclosure: campaign must be a known disclosure key",
  );
  console.assert(
    VARIANTS.includes(variant),
    "FTCDisclosure: variant must be banner or inline",
  );

  const copy = DISCLOSURE_COPY[campaign];
  console.assert(
    typeof copy === "string" && copy.length > 0,
    "FTCDisclosure: resolved copy must be a non-empty string",
  );

  const classes = variant === "banner" ? BANNER_CLASSES : INLINE_CLASSES;

  return (
    <aside
      role="note"
      aria-label="Affiliate disclosure"
      className={classes}
      data-ftc-disclosure={campaign}
    >
      <strong className="mr-2 font-semibold uppercase tracking-wide text-yellow-300">
        {DISCLOSURE_LABEL}:
      </strong>
      <span className="text-yellow-50">{copy}</span>
    </aside>
  );
}
