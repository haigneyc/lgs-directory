/**
 * Inline affiliate disclosure for FTC/EPN compliance.
 *
 * Must appear near every eBay affiliate link on the site.
 * See: https://www.ftc.gov/business-guidance/resources/disclosures-101-social-media-influencers
 */

const DISCLOSURE_TEXT =
  "As an eBay Partner, we may earn a commission if you make a purchase at no extra cost to you.";

interface AffiliateDisclosureProps {
  /** Optional className override for positioning */
  className?: string;
}

export function AffiliateDisclosure({ className }: AffiliateDisclosureProps) {
  console.assert(
    DISCLOSURE_TEXT.length > 0,
    "AffiliateDisclosure: disclosure text must not be empty",
  );
  console.assert(
    typeof className === "string" || className === undefined,
    "AffiliateDisclosure: className must be a string or undefined",
  );

  const baseClasses =
    "text-xs text-zinc-500 italic";

  return (
    <p className={className ? `${baseClasses} ${className}` : baseClasses}>
      {DISCLOSURE_TEXT}
    </p>
  );
}
