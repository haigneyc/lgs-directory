import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StoreStatusBadge, WpnBadge } from "@/components/status-badge";
import { HoursBadge } from "@/components/hours-badge";
import { formatCityState } from "@/lib/format";
import type { Store, StoreEnrichment } from "@/lib/types";
import { MapPin, Star } from "lucide-react";

const MAX_TABLE_ROWS = 100;

interface StoreTableProps {
  stores: Store[];
  enrichments?: Map<string, StoreEnrichment>;
}

export function StoreTable({ stores, enrichments }: StoreTableProps) {
  console.assert(Array.isArray(stores), "StoreTable: stores must be an array");
  console.assert(
    enrichments === undefined || enrichments instanceof Map,
    "StoreTable: enrichments must be a Map or undefined"
  );

  if (stores.length === 0) {
    return (
      <div className="text-center py-16 text-zinc-500">
        <p className="text-base">No stores found matching your filters.</p>
        <p className="text-sm mt-1 text-zinc-600">Try adjusting your search or filters.</p>
      </div>
    );
  }

  // Only show rating column if at least one store has a rating
  let hasAnyRating = false;
  if (enrichments !== undefined) {
    const checkLimit = Math.min(stores.length, 10_000);
    for (let i = 0; i < checkLimit; i++) {
      const e = enrichments.get(stores[i].id);
      if (e?.rating !== null && e?.rating !== undefined) {
        hasAnyRating = true;
        break;
      }
    }
  }

  return (
    <div className="overflow-x-auto">
    <Table>
      <TableHeader>
        <TableRow className="border-zinc-800/60 hover:bg-transparent">
          <TableHead className="text-zinc-400 font-display font-medium text-xs uppercase tracking-wider">Name</TableHead>
          <TableHead className="text-zinc-400 font-display font-medium text-xs uppercase tracking-wider">Location</TableHead>
          {enrichments !== undefined && (
            <TableHead className="text-zinc-400 font-display font-medium text-xs uppercase tracking-wider">Hours</TableHead>
          )}
          {hasAnyRating && (
            <TableHead className="text-zinc-400 font-display font-medium text-xs uppercase tracking-wider">Rating</TableHead>
          )}
          <TableHead className="text-zinc-400 font-display font-medium text-xs uppercase tracking-wider">Status</TableHead>
          <TableHead className="text-zinc-400 font-display font-medium text-xs uppercase tracking-wider">WPN</TableHead>
          <TableHead className="text-zinc-400 font-display font-medium text-xs uppercase tracking-wider">Source</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {stores.slice(0, MAX_TABLE_ROWS).map((store) => {
          const enrichment = enrichments?.get(store.id);
          return (
            <TableRow key={store.id} className="border-zinc-800/40 hover:bg-zinc-800/30 transition-colors">
              <TableCell>
                <Link
                  href={`/store/${store.id}`}
                  className="font-medium text-zinc-100 hover:text-yellow-500 transition-colors duration-200"
                >
                  {store.name}
                </Link>
              </TableCell>
              <TableCell>
                <span className="inline-flex items-center gap-1.5 text-zinc-400">
                  <MapPin className="w-3 h-3 text-zinc-600 flex-shrink-0" />
                  {formatCityState(store.address)}
                </span>
              </TableCell>
              {enrichments !== undefined && (
                <TableCell>
                  <HoursBadge
                    periods={enrichment?.hours_periods ?? null}
                    weekdayText={enrichment?.hours_weekday_text ?? null}
                    variant="compact"
                  />
                </TableCell>
              )}
              {hasAnyRating && (
                <TableCell className="text-sm">
                  {enrichment?.rating !== null && enrichment?.rating !== undefined ? (
                    <span className="inline-flex items-center gap-1">
                      <Star className="w-3 h-3 fill-yellow-500 text-yellow-500" />
                      <span className="text-zinc-300">{enrichment.rating.toFixed(1)}</span>
                    </span>
                  ) : (
                    <span className="text-zinc-700">{"\u2014"}</span>
                  )}
                </TableCell>
              )}
              <TableCell>
                <StoreStatusBadge status={store.status} />
              </TableCell>
              <TableCell>
                <WpnBadge level={store.wpn_level} />
              </TableCell>
              <TableCell className="text-zinc-600 text-xs font-mono">
                {store.discovery_source}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
    </div>
  );
}
