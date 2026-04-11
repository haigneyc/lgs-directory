"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";

const RESULTS_ELEMENT_ID = "results";

/**
 * Scrolls to the results section when search params indicate an active
 * query or filter. Covers both interactive searches (hero search bar,
 * filter bar) and direct URL visits with `?q=` or other filter params.
 *
 * Renders nothing — this is a behavior-only component.
 */
export function ScrollToResults() {
  const searchParams = useSearchParams();

  const hasFilters =
    searchParams.has("q") ||
    searchParams.has("state") ||
    searchParams.has("status") ||
    searchParams.has("wpn") ||
    searchParams.has("category") ||
    searchParams.has("game");

  console.assert(typeof hasFilters === "boolean", "ScrollToResults: hasFilters must be boolean");
  console.assert(typeof RESULTS_ELEMENT_ID === "string", "ScrollToResults: RESULTS_ELEMENT_ID must be a string");

  useEffect(() => {
    if (!hasFilters) {
      return;
    }

    const el = document.getElementById(RESULTS_ELEMENT_ID);
    if (el === null) {
      return;
    }

    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [hasFilters, searchParams]);

  return null;
}
