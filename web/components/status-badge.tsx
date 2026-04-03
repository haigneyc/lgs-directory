import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import type { StoreStatus, WpnLevel, PresenceStatus } from "@/lib/types";

const statusConfig: Record<StoreStatus, { color: string; description: string }> = {
  candidate: {
    color: "bg-zinc-500/15 text-zinc-400 border-zinc-500/30",
    description: "Discovered but not yet validated",
  },
  verified: {
    color: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    description: "Confirmed to exist with a working website",
  },
  active: {
    color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    description: "Fully validated — online, sells MTG singles",
  },
  unresponsive: {
    color: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    description: "Website is down or unreachable",
  },
  closed: {
    color: "bg-red-500/15 text-red-400 border-red-500/30",
    description: "Confirmed permanently closed",
  },
};

const wpnConfig: Record<WpnLevel, { color: string; description: string }> = {
  core: {
    color: "bg-indigo-500/15 text-indigo-400 border-indigo-500/30",
    description: "Wizards Play Network — Core level store",
  },
  premium: {
    color: "bg-purple-500/15 text-purple-400 border-purple-500/30",
    description: "Wizards Play Network — Premium level store",
  },
};

const presenceConfig: Record<PresenceStatus, { color: string; description: string }> = {
  active: {
    color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    description: "URL is reachable and operational",
  },
  unreachable: {
    color: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    description: "URL returns errors or times out",
  },
  dead: {
    color: "bg-red-500/15 text-red-400 border-red-500/30",
    description: "URL is confirmed defunct (404, domain expired)",
  },
};

export function StoreStatusBadge({ status }: { status: StoreStatus }) {
  const cfg = statusConfig[status];
  return (
    <Tooltip>
      <TooltipTrigger>
        <Badge variant="outline" className={cfg.color}>
          {status}
        </Badge>
      </TooltipTrigger>
      <TooltipContent>{cfg.description}</TooltipContent>
    </Tooltip>
  );
}

export function WpnBadge({ level }: { level: WpnLevel | null }) {
  if (!level) return null;
  const cfg = wpnConfig[level];
  return (
    <Tooltip>
      <TooltipTrigger>
        <Badge variant="outline" className={cfg.color}>
          WPN {level}
        </Badge>
      </TooltipTrigger>
      <TooltipContent>{cfg.description}</TooltipContent>
    </Tooltip>
  );
}

export function PresenceStatusBadge({ status }: { status: PresenceStatus }) {
  const cfg = presenceConfig[status];
  return (
    <Tooltip>
      <TooltipTrigger>
        <Badge variant="outline" className={cfg.color}>
          {status}
        </Badge>
      </TooltipTrigger>
      <TooltipContent>{cfg.description}</TooltipContent>
    </Tooltip>
  );
}
