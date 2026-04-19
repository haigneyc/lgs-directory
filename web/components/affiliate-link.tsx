import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type AffiliateNetwork = "amazon" | "ebay" | "tcgplayer";

interface AffiliateLinkProps {
  href: string;
  network: AffiliateNetwork;
  placement: string;
  className?: string;
  children: ReactNode;
  title?: string;
}

const AFFILIATE_REL = "sponsored noopener noreferrer";

export function AffiliateLink({
  href,
  network,
  placement,
  className,
  children,
  title,
}: AffiliateLinkProps) {
  console.assert(typeof href === "string" && href.length > 0, "AffiliateLink: href must be non-empty");
  console.assert(
    (network === "amazon" || network === "ebay" || network === "tcgplayer") &&
      typeof placement === "string" &&
      placement.length > 0,
    "AffiliateLink: network and placement must be valid",
  );

  return (
    <a
      href={href}
      target="_blank"
      rel={AFFILIATE_REL}
      data-affiliate-network={network}
      data-affiliate-placement={placement}
      data-affiliate-destination-url={href}
      className={cn(className)}
      title={title}
    >
      {children}
    </a>
  );
}
