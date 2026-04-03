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
import { formatCityState } from "@/lib/format";
import type { Store, StoreEnrichment } from "@/lib/types";

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
      <div className="text-center py-12 text-zinc-500">
        No stores found matching your filters.
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
        <TableRow className="border-zinc-800 hover:bg-transparent">
          <TableHead className="text-zinc-400">Name</TableHead>
          <TableHead className="text-zinc-400">Location</TableHead>
          {hasAnyRating && (
            <TableHead className="text-zinc-400">Rating</TableHead>
          )}
          <TableHead className="text-zinc-400">Status</TableHead>
          <TableHead className="text-zinc-400">WPN</TableHead>
          <TableHead className="text-zinc-400">Source</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {stores.map((store) => {
          const enrichment = enrichments?.get(store.id);
          return (
            <TableRow key={store.id} className="border-zinc-800 hover:bg-zinc-900/50">
              <TableCell>
                <Link
                  href={`/store/${store.id}`}
                  className="font-medium text-zinc-50 hover:text-blue-400 transition-colors"
                >
                  {store.name}
                </Link>
              </TableCell>
              <TableCell className="text-zinc-400">
                {formatCityState(store.address)}
              </TableCell>
              {hasAnyRating && (
                <TableCell className="text-sm">
                  {enrichment?.rating !== null && enrichment?.rating !== undefined ? (
                    <span>
                      <span className="text-amber-400">{"\u2605"}</span>{" "}
                      <span className="text-zinc-300">{enrichment.rating.toFixed(1)}</span>
                    </span>
                  ) : (
                    <span className="text-zinc-600">{"\u2014"}</span>
                  )}
                </TableCell>
              )}
              <TableCell>
                <StoreStatusBadge status={store.status} />
              </TableCell>
              <TableCell>
                <WpnBadge level={store.wpn_level} />
              </TableCell>
              <TableCell className="text-zinc-500 text-xs font-mono">
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
