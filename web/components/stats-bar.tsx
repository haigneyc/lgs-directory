import { Store, CheckCircle, Award, Globe } from "lucide-react";

interface StatsBarProps {
  storeCount: number;
  activeCount: number;
  wpnPremiumCount: number;
  onlineCount: number;
}

export function StatsBar({
  storeCount,
  activeCount,
  wpnPremiumCount,
  onlineCount,
}: StatsBarProps) {
  console.assert(storeCount >= 0, "StatsBar: storeCount must be non-negative");
  console.assert(activeCount >= 0, "StatsBar: activeCount must be non-negative");

  return (
    <div className="flex flex-wrap gap-4 mb-6">
      <div className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2">
        <Store className="w-3.5 h-3.5 text-zinc-500" />
        <span className="font-display font-semibold text-zinc-200">{storeCount.toLocaleString()}</span>
        <span className="text-xs text-zinc-500">stores</span>
      </div>
      <div className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2">
        <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
        <span className="font-display font-semibold text-emerald-400">{activeCount.toLocaleString()}</span>
        <span className="text-xs text-zinc-500">active</span>
      </div>
      <div className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2">
        <Award className="w-3.5 h-3.5 text-purple-400" />
        <span className="font-display font-semibold text-purple-400">{wpnPremiumCount.toLocaleString()}</span>
        <span className="text-xs text-zinc-500">WPN Premium</span>
      </div>
      <div className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/50 px-3 py-2">
        <Globe className="w-3.5 h-3.5 text-blue-400" />
        <span className="font-display font-semibold text-blue-400">{onlineCount.toLocaleString()}</span>
        <span className="text-xs text-zinc-500">sell online</span>
      </div>
    </div>
  );
}
