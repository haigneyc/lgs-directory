import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { PresenceStatusBadge } from "@/components/status-badge";
import { formatPlatform, formatDate } from "@/lib/format";
import type { OnlinePresence } from "@/lib/types";

function SinglesBadge({
  sells,
  size,
}: {
  sells: boolean | null;
  size: string | null;
}) {
  if (sells === null) {
    return <span className="text-zinc-600">—</span>;
  }
  if (!sells) {
    return <span className="text-zinc-500">No</span>;
  }
  return (
    <span className="text-emerald-400">
      Yes{size && size !== "none" ? ` (${size})` : ""}
    </span>
  );
}

export function PresenceTable({
  presences,
}: {
  presences: OnlinePresence[];
}) {
  if (presences.length === 0) {
    return (
      <p className="text-zinc-500 text-sm py-4">
        No online presences recorded.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow className="border-zinc-800 hover:bg-transparent">
          <TableHead className="text-zinc-400">Channel</TableHead>
          <TableHead className="text-zinc-400">URL</TableHead>
          <TableHead className="text-zinc-400">Platform</TableHead>
          <TableHead className="text-zinc-400">Singles</TableHead>
          <TableHead className="text-zinc-400">Pricing</TableHead>
          <TableHead className="text-zinc-400">Status</TableHead>
          <TableHead className="text-zinc-400">Last Checked</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {presences.map((p) => (
          <TableRow key={p.id} className="border-zinc-800 hover:bg-zinc-900/50">
            <TableCell>
              <Badge
                variant="outline"
                className="bg-zinc-800/50 text-zinc-300 border-zinc-700"
              >
                {p.channel_type}
              </Badge>
            </TableCell>
            <TableCell className="max-w-xs truncate">
              <a
                href={p.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-400 hover:text-blue-300 transition-colors text-sm"
              >
                {p.url.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "")}
              </a>
            </TableCell>
            <TableCell className="text-zinc-300 text-sm">
              {p.platform ? formatPlatform(p.platform) : "—"}
            </TableCell>
            <TableCell>
              <SinglesBadge
                sells={p.sells_mtg_singles}
                size={p.estimated_inventory_size}
              />
            </TableCell>
            <TableCell className="text-zinc-400 text-sm">
              {p.pricing_method ?? "—"}
            </TableCell>
            <TableCell>
              <PresenceStatusBadge status={p.status} />
            </TableCell>
            <TableCell className="text-zinc-500 text-xs">
              {formatDate(p.last_checked)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
