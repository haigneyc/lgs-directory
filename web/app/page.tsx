import { Suspense } from "react";
import Link from "next/link";
import { listStores, getFilterOptions, getStateIndex } from "@/lib/queries";
import { abbreviationToStateName } from "@/lib/slugs";
import { StoreTable } from "@/components/store-table";
import { FilterBar } from "@/components/filter-bar";
import { Pagination } from "@/components/pagination";

interface PageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export default async function HomePage({ searchParams }: PageProps) {
  const params = await searchParams;

  const rawPage =
    typeof params.page === "string" ? parseInt(params.page, 10) : 1;
  const state = typeof params.state === "string" ? params.state : undefined;
  const status = typeof params.status === "string" ? params.status : undefined;
  const wpnLevel = typeof params.wpn === "string" ? params.wpn : undefined;
  const search = typeof params.q === "string" ? params.q : undefined;
  const category = typeof params.category === "string" ? params.category : undefined;

  const [initialResult, filterOptions, states] = await Promise.all([
    listStores({ page: rawPage, state, status, wpnLevel, search, category }),
    getFilterOptions(),
    getStateIndex(),
  ]);

  // Clamp page to valid range so out-of-range pages show the last valid page
  const totalPages =
    Math.ceil(initialResult.total / initialResult.pageSize) || 1;
  const safePage = Math.min(Math.max(1, rawPage), totalPages);

  // Re-fetch with clamped page only if the requested page was out of range
  const result =
    safePage === rawPage
      ? initialResult
      : await listStores({ page: safePage, state, status, wpnLevel, search, category });

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight mb-1">
          Browse Stores
        </h1>
        <p className="text-sm text-zinc-500">
          US Local Game Stores with online presence data
        </p>
      </div>

      <Suspense fallback={null}>
        <FilterBar
          states={filterOptions.states}
          statuses={filterOptions.statuses}
          wpnLevels={filterOptions.wpnLevels}
          categories={filterOptions.categories}
        />
      </Suspense>

      <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-950">
        <StoreTable stores={result.stores} />
      </div>

      <Suspense fallback={null}>
        <Pagination
          page={result.page}
          pageSize={result.pageSize}
          total={result.total}
        />
      </Suspense>

      {states.length > 0 && (
        <div className="mt-12 border-t border-zinc-800 pt-8">
          <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-3">
            Browse by State
          </h2>
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
            {states.map((s) => (
              <Link
                key={s.slug}
                href={`/stores/${s.slug}`}
                className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
              >
                {abbreviationToStateName(s.state) ?? s.state} ({s.store_count})
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
