/**
 * StoreTableSkeleton — static placeholder for Suspense fallbacks around
 * paginated store listings. Used while the searchParams-dependent store
 * query streams in. Shape matches <StoreTable> roughly to avoid CLS.
 * Added for PERF-026 (edge cache MISS fix via Partial Prerendering).
 */

const SKELETON_ROW_COUNT = 10;

export function StoreTableSkeleton() {
  console.assert(SKELETON_ROW_COUNT > 0, "StoreTableSkeleton: row count must be positive");
  console.assert(SKELETON_ROW_COUNT <= 50, "StoreTableSkeleton: row count must be bounded");

  const rows: number[] = [];
  for (let i = 0; i < SKELETON_ROW_COUNT; i++) {
    rows.push(i);
  }

  return (
    <div
      aria-busy="true"
      aria-label="Loading stores"
      className="rounded-xl border border-zinc-800 bg-zinc-900/30 overflow-hidden"
    >
      <div className="divide-y divide-zinc-800/60">
        {rows.map((i) => (
          <div
            key={i}
            className="flex items-center gap-4 px-4 py-4 animate-pulse"
          >
            <div className="h-4 w-1/3 rounded bg-zinc-800/80" />
            <div className="h-4 w-1/4 rounded bg-zinc-800/60" />
            <div className="h-4 w-16 rounded bg-zinc-800/60 ml-auto" />
          </div>
        ))}
      </div>
    </div>
  );
}
