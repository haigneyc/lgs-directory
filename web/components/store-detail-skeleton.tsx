/**
 * Skeleton placeholder for the `/store/[slug]` detail page body.
 *
 * Rendered as the Suspense fallback while the dynamic store data is
 * being fetched. Shape mirrors the rendered store detail page so that
 * cumulative layout shift is minimised when the real content streams
 * in. Heights and widths use the same Tailwind utility classes as the
 * actual page so the swap is visually stable.
 */
export function StoreDetailSkeleton(): React.ReactElement {
  return (
    <div
      aria-busy="true"
      aria-label="Loading store details"
      className="animate-pulse"
    >
      {/* Header block — name, rating, address, badges */}
      <div className="mt-6 mb-8">
        <div className="flex flex-wrap items-start gap-4">
          <div className="flex-1 min-w-0 space-y-3">
            <div className="h-9 w-2/3 rounded bg-zinc-800" />
            <div className="h-5 w-32 rounded bg-zinc-800/70" />
            <div className="space-y-2">
              <div className="h-4 w-3/4 rounded bg-zinc-800/70" />
              <div className="h-4 w-1/3 rounded bg-zinc-800/70" />
            </div>
            <div className="h-6 w-40 rounded bg-zinc-800/70" />
          </div>
          <div className="flex flex-wrap items-center gap-2 flex-shrink-0">
            <div className="h-6 w-20 rounded bg-zinc-800" />
            <div className="h-6 w-16 rounded bg-zinc-800" />
            <div className="h-6 w-24 rounded bg-zinc-800" />
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 mt-4">
          <div className="h-6 w-16 rounded bg-zinc-800/70" />
          <div className="h-6 w-20 rounded bg-zinc-800/70" />
          <div className="h-6 w-14 rounded bg-zinc-800/70" />
        </div>
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 space-y-8">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 space-y-3">
            <div className="h-5 w-24 rounded bg-zinc-800" />
            <div className="h-4 w-full rounded bg-zinc-800/70" />
            <div className="h-4 w-5/6 rounded bg-zinc-800/70" />
            <div className="h-4 w-4/6 rounded bg-zinc-800/70" />
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 space-y-3">
            <div className="h-5 w-40 rounded bg-zinc-800" />
            <div className="flex flex-wrap gap-2">
              <div className="h-6 w-16 rounded bg-zinc-800/70" />
              <div className="h-6 w-20 rounded bg-zinc-800/70" />
              <div className="h-6 w-14 rounded bg-zinc-800/70" />
              <div className="h-6 w-24 rounded bg-zinc-800/70" />
            </div>
          </div>
          <div className="rounded-xl border border-zinc-800 overflow-hidden">
            <div className="px-6 py-4 bg-zinc-900/50 border-b border-zinc-800">
              <div className="h-5 w-28 rounded bg-zinc-800" />
            </div>
            <div className="h-72 bg-zinc-900/40" />
          </div>
        </div>
        <div className="space-y-6">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 space-y-4">
            <div className="h-4 w-28 rounded bg-zinc-800" />
            <div className="space-y-3">
              <div>
                <div className="h-3 w-24 rounded bg-zinc-800/70 mb-1" />
                <div className="h-4 w-32 rounded bg-zinc-800/70" />
              </div>
              <div>
                <div className="h-3 w-20 rounded bg-zinc-800/70 mb-1" />
                <div className="h-4 w-28 rounded bg-zinc-800/70" />
              </div>
              <div>
                <div className="h-3 w-24 rounded bg-zinc-800/70 mb-1" />
                <div className="h-4 w-28 rounded bg-zinc-800/70" />
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 space-y-2">
            <div className="h-4 w-16 rounded bg-zinc-800 mb-3" />
            <div className="h-3 w-40 rounded bg-zinc-800/70" />
            <div className="h-3 w-36 rounded bg-zinc-800/70" />
            <div className="h-3 w-40 rounded bg-zinc-800/70" />
            <div className="h-3 w-32 rounded bg-zinc-800/70" />
          </div>
        </div>
      </div>
    </div>
  );
}
