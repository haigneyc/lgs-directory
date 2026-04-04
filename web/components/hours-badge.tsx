"use client";

import { useSyncExternalStore } from "react";
import { Badge } from "@/components/ui/badge";
import { getStoreHoursStatus } from "@/lib/hours";
import type { HoursPeriod } from "@/lib/types";

interface HoursBadgeProps {
  periods: HoursPeriod[] | null;
  weekdayText: string[] | null;
  /** "detail" shows full info; "compact" shows just badge. */
  variant?: "detail" | "compact";
}

/** Subscribe is a no-op since mount status never changes after hydration. */
function subscribeNoop(callback: () => void): () => void {
  // Not subscribing to any external store; we only need the server/client
  // snapshot distinction.
  void callback;
  return () => {};
}

function getClientSnapshot(): boolean {
  return true;
}

function getServerSnapshot(): boolean {
  return false;
}

/**
 * Displays real-time open/closed status for a store.
 *
 * Client component: computes status from the viewer's local clock.
 * Returns a placeholder during SSR to avoid hydration mismatch (the
 * server doesn't know the user's timezone), then shows the live badge
 * after hydration.
 */
export function HoursBadge({
  periods,
  weekdayText,
  variant = "detail",
}: HoursBadgeProps) {
  console.assert(
    periods === null || Array.isArray(periods),
    "HoursBadge: periods must be an array or null"
  );
  console.assert(
    weekdayText === null || Array.isArray(weekdayText),
    "HoursBadge: weekdayText must be an array or null"
  );

  const isClient = useSyncExternalStore(
    subscribeNoop,
    getClientSnapshot,
    getServerSnapshot
  );

  // No hours data at all
  if (periods === null && weekdayText === null) {
    if (variant === "detail") {
      return (
        <span className="text-xs text-zinc-500">Hours not available</span>
      );
    }
    return null;
  }

  // Don't render time-dependent content during SSR to avoid hydration mismatch
  if (!isClient) {
    return (
      <span className="text-xs text-zinc-500">Loading hours...</span>
    );
  }

  const status = getStoreHoursStatus(periods, weekdayText);

  if (status.todayHours === null && !status.isOpen) {
    if (variant === "detail") {
      return (
        <span className="text-xs text-zinc-500">Hours not available</span>
      );
    }
    return null;
  }

  if (status.isOpen) {
    return (
      <span className="inline-flex items-center gap-2">
        <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30">
          Open
        </Badge>
        {variant === "detail" && status.todayHours !== null && (
          <span className="text-xs text-zinc-400">
            Today: {status.todayHours}
          </span>
        )}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-2">
      <Badge className="bg-zinc-500/15 text-zinc-400 border-zinc-500/30">
        Closed
      </Badge>
      {variant === "detail" && status.nextOpen !== null && (
        <span className="text-xs text-zinc-500">
          {status.nextOpen}
        </span>
      )}
      {variant === "detail" && status.nextOpen === null && status.todayHours !== null && status.todayHours !== "Closed" && (
        <span className="text-xs text-zinc-400">
          Today: {status.todayHours}
        </span>
      )}
    </span>
  );
}
