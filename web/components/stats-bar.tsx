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
    <div className="flex flex-wrap gap-x-3 gap-y-1 text-sm text-zinc-400 mb-4">
      <span>{storeCount.toLocaleString()} stores</span>
      <span className="text-zinc-600">·</span>
      <span>
        <span className="text-emerald-400">{activeCount.toLocaleString()}</span>{" "}
        active
      </span>
      <span className="text-zinc-600">·</span>
      <span>
        <span className="text-purple-400">{wpnPremiumCount.toLocaleString()}</span>{" "}
        WPN Premium
      </span>
      <span className="text-zinc-600">·</span>
      <span>
        <span className="text-blue-400">{onlineCount.toLocaleString()}</span>{" "}
        sell online
      </span>
    </div>
  );
}
