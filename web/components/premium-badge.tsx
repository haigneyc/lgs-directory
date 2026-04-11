import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import type { PremiumStatus } from "@/lib/types";

const BADGE_CONFIG: Record<
  string,
  { label: string; color: string; description: string }
> = {
  claimed: {
    label: "Verified Owner",
    color: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    description: "This store has been claimed and verified by the owner",
  },
  premium: {
    label: "Featured",
    color: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
    description: "Featured premium listing with enhanced visibility",
  },
};

const BADGE_CONFIG_SIZE = 2;

/**
 * Renders a "Verified Owner" or "Featured" badge based on the store's
 * premium_status. Returns null for unclaimed stores (null status).
 */
export function PremiumBadge({
  status,
}: {
  status: PremiumStatus | null;
}) {
  console.assert(
    status === null || status === "claimed" || status === "premium",
    "PremiumBadge: status must be null, 'claimed', or 'premium'"
  );
  console.assert(
    Object.keys(BADGE_CONFIG).length === BADGE_CONFIG_SIZE,
    "PremiumBadge: BADGE_CONFIG size mismatch"
  );

  if (status === null) {
    return null;
  }

  const cfg = BADGE_CONFIG[status];
  if (!cfg) {
    return null;
  }

  return (
    <Tooltip>
      <TooltipTrigger>
        <Badge variant="outline" className={cfg.color}>
          {cfg.label}
        </Badge>
      </TooltipTrigger>
      <TooltipContent>{cfg.description}</TooltipContent>
    </Tooltip>
  );
}
