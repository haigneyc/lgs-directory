"use client";

import { useEffect } from "react";

const AFFILIATE_SELECTOR =
  "a[data-affiliate-network][data-affiliate-placement]";

type Gtag = (
  command: "event",
  eventName: string,
  params: Record<string, unknown>
) => void;

declare global {
  interface Window {
    gtag?: Gtag;
  }
}

function trackAffiliateAnchor(anchor: HTMLAnchorElement) {
  const network = anchor.dataset.affiliateNetwork;
  const placement = anchor.dataset.affiliatePlacement;
  const destinationUrl = anchor.dataset.affiliateDestinationUrl ?? anchor.href;

  console.assert(
    typeof network === "string" && network.length > 0,
    "trackAffiliateAnchor: network must be present",
  );
  console.assert(
    typeof placement === "string" && placement.length > 0,
    "trackAffiliateAnchor: placement must be present",
  );

  if (
    typeof network !== "string" ||
    network.length === 0 ||
    typeof placement !== "string" ||
    placement.length === 0
  ) {
    return;
  }

  if (typeof window.gtag !== "function") {
    return;
  }

  window.gtag("event", "affiliate_click", {
    network,
    placement,
    destination_url: destinationUrl,
    page: window.location.pathname,
    transport_type: "beacon",
  });
}

export function AffiliateClickTracker() {
  useEffect(() => {
    console.assert(
      typeof AFFILIATE_SELECTOR === "string" && AFFILIATE_SELECTOR.length > 0,
      "AffiliateClickTracker: selector must be non-empty",
    );
    console.assert(
      typeof document !== "undefined",
      "AffiliateClickTracker: document must exist in the browser",
    );

    function handleAffiliateEvent(event: MouseEvent) {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }

      const anchor = target.closest(AFFILIATE_SELECTOR);
      console.assert(
        anchor === null || anchor instanceof HTMLAnchorElement,
        "handleAffiliateEvent: anchor must be an affiliate anchor",
      );
      console.assert(
        typeof AFFILIATE_SELECTOR === "string" && AFFILIATE_SELECTOR.length > 0,
        "handleAffiliateEvent: selector must be non-empty",
      );

      if (anchor instanceof HTMLAnchorElement) {
        trackAffiliateAnchor(anchor);
      }
    }

    document.addEventListener("click", handleAffiliateEvent, true);
    document.addEventListener("auxclick", handleAffiliateEvent, true);

    return () => {
      document.removeEventListener("click", handleAffiliateEvent, true);
      document.removeEventListener("auxclick", handleAffiliateEvent, true);
    };
  }, []);

  return null;
}
