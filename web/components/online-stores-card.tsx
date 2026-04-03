import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { formatPlatform } from "@/lib/format";
import type { OnlineStore } from "@/lib/types";

interface OnlineStoresCardProps {
  stores: OnlineStore[];
}

const MAX_DISPLAY = 20;

export function OnlineStoresCard({ stores }: OnlineStoresCardProps) {
  console.assert(Array.isArray(stores), "OnlineStoresCard: stores must be an array");
  console.assert(MAX_DISPLAY > 0, "OnlineStoresCard: MAX_DISPLAY must be positive");

  if (stores.length === 0) {
    return null;
  }

  const displayed = stores.slice(0, MAX_DISPLAY);

  return (
    <section>
      <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-3">
        Buy Cards Online
      </h2>
      <div className="rounded-lg border border-zinc-800 bg-zinc-950 divide-y divide-zinc-800">
        {displayed.map((store) => {
          const platformLabel = store.platform ? formatPlatform(store.platform) : null;
          const inventoryLabel = store.estimated_inventory_size
            ? store.estimated_inventory_size
            : null;
          const subtitle = [platformLabel, inventoryLabel]
            .filter(Boolean)
            .join(" · ");

          return (
            <div
              key={store.store_id}
              className="flex items-center justify-between px-4 py-3 gap-4"
            >
              <div className="min-w-0">
                <Link
                  href={`/store/${store.store_id}`}
                  className="text-sm text-zinc-300 hover:text-white transition-colors truncate block"
                >
                  {store.store_name}
                </Link>
                {subtitle && (
                  <p className="text-xs text-zinc-500 mt-0.5">{subtitle}</p>
                )}
              </div>
              <a
                href={store.presence_url}
                rel="nofollow sponsored noopener"
                target="_blank"
                className="shrink-0"
              >
                <Badge variant="outline" className="border-zinc-700 text-zinc-400 hover:text-zinc-300 hover:border-zinc-500 transition-colors cursor-pointer">
                  Visit Shop ↗
                </Badge>
              </a>
            </div>
          );
        })}
      </div>
    </section>
  );
}
