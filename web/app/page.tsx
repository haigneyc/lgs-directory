import { Suspense } from "react";
import Link from "next/link";
import {
  listStores,
  getFilterOptions,
  getStateIndex,
  getCategoryStats,
  getTotalStoreCount,
  getPopularCities,
  getGameTagCounts,
} from "@/lib/queries";
import { abbreviationToStateName } from "@/lib/slugs";
import { stateToSlug, cityToSlug } from "@/lib/slugs";
import { formatProduct } from "@/lib/format";
import { StoreTable } from "@/components/store-table";
import { FilterBar } from "@/components/filter-bar";
import { Pagination } from "@/components/pagination";
import { HeroSearch } from "@/components/hero-search";
import {
  Sword,
  BookOpen,
  Gamepad2,
  Shield,
  MapPin,
  Store,
  Star,
  TrendingUp,
} from "lucide-react";

interface PageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

/** Game category config for display cards on the homepage */
const GAME_CATEGORIES = [
  { key: "mtg", label: "Magic: The Gathering", icon: "MTG", color: "from-violet-500/20 to-violet-900/10 border-violet-500/20 hover:border-violet-400/40" },
  { key: "pokemon", label: "Pokemon TCG", icon: "PKM", color: "from-yellow-500/20 to-yellow-900/10 border-yellow-500/20 hover:border-yellow-400/40" },
  { key: "yugioh", label: "Yu-Gi-Oh!", icon: "YGO", color: "from-red-500/20 to-red-900/10 border-red-500/20 hover:border-red-400/40" },
  { key: "fab", label: "Flesh and Blood", icon: "FAB", color: "from-rose-500/20 to-rose-900/10 border-rose-500/20 hover:border-rose-400/40" },
  { key: "dnd", label: "D&D / RPGs", icon: "RPG", color: "from-emerald-500/20 to-emerald-900/10 border-emerald-500/20 hover:border-emerald-400/40" },
  { key: "board_games", label: "Board Games", icon: "BG", color: "from-blue-500/20 to-blue-900/10 border-blue-500/20 hover:border-blue-400/40" },
  { key: "miniatures", label: "Miniatures", icon: "MINI", color: "from-orange-500/20 to-orange-900/10 border-orange-500/20 hover:border-orange-400/40" },
  { key: "comics", label: "Comics", icon: "CMX", color: "from-cyan-500/20 to-cyan-900/10 border-cyan-500/20 hover:border-cyan-400/40" },
] as const;

const GAME_CATEGORIES_LENGTH = 8;

/** Store type cards linking to category pages */
const STORE_TYPES = [
  { href: "/", label: "Game Stores", description: "MTG, Pokemon, board games, and more", icon: Sword, dbCategory: "lgs" },
  { href: "/comics", label: "Comic Shops", description: "New releases, back issues, graphic novels", icon: BookOpen, dbCategory: "comic_shop" },
  { href: "/retro-games", label: "Retro Games", description: "Classic consoles, cartridges, vintage gaming", icon: Gamepad2, dbCategory: "retro_games" },
  { href: "/warhammer", label: "Warhammer & Hobby", description: "Miniatures, paints, tabletop wargaming", icon: Shield, dbCategory: "hobby_miniatures" },
] as const;

const STORE_TYPES_LENGTH = 4;

export default async function HomePage({ searchParams }: PageProps) {
  const params = await searchParams;

  console.assert(GAME_CATEGORIES.length === GAME_CATEGORIES_LENGTH, "HomePage: GAME_CATEGORIES count mismatch");
  console.assert(STORE_TYPES.length === STORE_TYPES_LENGTH, "HomePage: STORE_TYPES count mismatch");

  const hasFilters = typeof params.page === "string" ||
    typeof params.state === "string" ||
    typeof params.status === "string" ||
    typeof params.wpn === "string" ||
    typeof params.q === "string" ||
    typeof params.category === "string";

  const rawPage =
    typeof params.page === "string" ? parseInt(params.page, 10) : 1;
  const state = typeof params.state === "string" ? params.state : undefined;
  const status = typeof params.status === "string" ? params.status : undefined;
  const wpnLevel = typeof params.wpn === "string" ? params.wpn : undefined;
  const search = typeof params.q === "string" ? params.q : undefined;
  const category = typeof params.category === "string" ? params.category : undefined;

  const [initialResult, filterOptions, states, categoryStats, totalCount, popularCities, gameTags] = await Promise.all([
    listStores({ page: rawPage, state, status, wpnLevel, search, category }),
    getFilterOptions(),
    getStateIndex(),
    hasFilters ? Promise.resolve([]) : getCategoryStats(),
    hasFilters ? Promise.resolve(0) : getTotalStoreCount(),
    hasFilters ? Promise.resolve([]) : getPopularCities(12),
    hasFilters ? Promise.resolve([]) : getGameTagCounts(),
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

  // Build a map of game tag -> store count
  const tagCountMap = new Map<string, number>();
  const tagLimit = Math.min(gameTags.length, 100);
  for (let i = 0; i < tagLimit; i++) {
    tagCountMap.set(gameTags[i].tag, gameTags[i].count);
  }

  // Build a map of category -> store count
  const categoryCountMap = new Map<string, number>();
  const catLimit = Math.min(categoryStats.length, 20);
  for (let i = 0; i < catLimit; i++) {
    categoryCountMap.set(categoryStats[i].category, categoryStats[i].count);
  }

  // Compute categorized total with bounded loop
  let categorizedTotal = 0;
  for (let i = 0; i < catLimit; i++) {
    categorizedTotal += categoryStats[i].count;
  }

  // Compute state count -- DC is included as a "state" in the data but is not
  // technically a state, so we separate it for display accuracy.
  const includesDC = states.some((s) => s.state === "DC");
  const usStateCount = includesDC ? states.length - 1 : states.length;

  return (
    <div>
      {/* Hero Section -- only shown when not filtering */}
      {!hasFilters && (
        <>
          <section className="relative overflow-hidden border-b border-amber-900/20 parchment-texture">
            {/* Background gradient -- warm candlelight glow */}
            <div className="absolute inset-0 bg-gradient-to-b from-stone-900 via-zinc-950 to-zinc-950" />
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-amber-600/8 via-red-900/3 to-transparent" />

            <div className="relative mx-auto max-w-7xl px-4 lg:px-6 pt-16 pb-12">
              <div className="max-w-3xl mx-auto text-center">
                <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-4">
                  <span className="bg-gradient-to-r from-stone-100 via-amber-50 to-stone-300 bg-clip-text text-transparent">
                    Find Your Local
                  </span>
                  <br />
                  <span className="bg-gradient-to-r from-amber-400 via-yellow-500 to-amber-600 bg-clip-text text-transparent">
                    Game Store
                  </span>
                </h1>
                <p className="text-lg text-zinc-400 mb-8 max-w-xl mx-auto leading-relaxed">
                  The most comprehensive directory of game stores, comic shops, and hobby stores across the United States.
                </p>

                {/* Hero search */}
                <HeroSearch />
              </div>

              {/* Quick stats */}
              <div className="mt-12 flex flex-wrap items-center justify-center gap-8 text-center">
                <div className="flex items-center gap-2">
                  <Store className="w-4 h-4 text-yellow-500" />
                  <span className="font-display text-2xl font-bold text-zinc-50">{totalCount.toLocaleString()}</span>
                  <span className="text-sm text-zinc-500">stores</span>
                </div>
                <div className="w-px h-6 bg-zinc-800" />
                <div className="flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-emerald-400" />
                  <span className="font-display text-2xl font-bold text-zinc-50">{usStateCount}</span>
                  <span className="text-sm text-zinc-500">{includesDC ? "states + DC" : "states"}</span>
                </div>
                <div className="w-px h-6 bg-zinc-800" />
                <div className="flex items-center gap-2">
                  <Star className="w-4 h-4 text-purple-400" />
                  <span className="font-display text-2xl font-bold text-zinc-50">
                    {categorizedTotal.toLocaleString()}
                  </span>
                  <span className="text-sm text-zinc-500">categorized</span>
                </div>
              </div>
            </div>
          </section>

          {/* Game Category Cards */}
          <section className="mx-auto max-w-7xl px-4 lg:px-6 py-12">
            <div className="flex items-center gap-3 mb-6">
              <TrendingUp className="w-5 h-5 text-yellow-500" />
              <h2 className="font-display text-xl font-semibold tracking-tight">
                Browse by Game
              </h2>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {GAME_CATEGORIES.map((game) => {
                const count = tagCountMap.get(game.key) ?? 0;
                return (
                  <Link
                    key={game.key}
                    href={`/?q=${encodeURIComponent(formatProduct(game.key))}`}
                    className={`group relative rounded-xl border bg-gradient-to-br p-4 transition-all duration-200 hover:scale-[1.02] hover:shadow-lg ${game.color}`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <span className="text-xs font-mono font-bold text-zinc-500 group-hover:text-zinc-400 transition-colors">
                        {game.icon}
                      </span>
                      {count > 0 && (
                        <span className="text-xs text-zinc-600 font-medium">
                          {count.toLocaleString()} stores
                        </span>
                      )}
                    </div>
                    <p className="text-sm font-medium text-zinc-200 group-hover:text-zinc-50 transition-colors">
                      {game.label}
                    </p>
                  </Link>
                );
              })}
            </div>
          </section>

          {/* Store Type Cards */}
          <section className="mx-auto max-w-7xl px-4 lg:px-6 pb-12">
            <div className="flex items-center gap-3 mb-6">
              <Store className="w-5 h-5 text-yellow-500" />
              <h2 className="font-display text-xl font-semibold tracking-tight">
                Store Types
              </h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {STORE_TYPES.map((type) => {
                const Icon = type.icon;
                const count = categoryCountMap.get(type.dbCategory) ?? 0;
                return (
                  <Link
                    key={type.href}
                    href={type.href}
                    className="group rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 transition-all duration-200 hover:bg-zinc-800/70 hover:border-zinc-700 hover:shadow-lg"
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-yellow-600/10 text-yellow-500 group-hover:bg-yellow-600/20 transition-colors">
                        <Icon className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="font-display font-semibold text-zinc-100 group-hover:text-zinc-50 transition-colors">
                          {type.label}
                        </h3>
                        {count > 0 && (
                          <p className="text-xs text-zinc-500">{count.toLocaleString()} stores</p>
                        )}
                      </div>
                    </div>
                    <p className="text-sm text-zinc-500 group-hover:text-zinc-400 transition-colors">
                      {type.description}
                    </p>
                  </Link>
                );
              })}
            </div>
          </section>

          {/* Popular Cities */}
          {popularCities.length > 0 && (
            <section className="mx-auto max-w-7xl px-4 lg:px-6 pb-12">
              <div className="flex items-center gap-3 mb-6">
                <MapPin className="w-5 h-5 text-yellow-500" />
                <h2 className="font-display text-xl font-semibold tracking-tight">
                  Popular Cities
                </h2>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {popularCities.map((city) => (
                  <Link
                    key={`${city.city}-${city.state}`}
                    href={`/stores/${stateToSlug(city.state)}/${cityToSlug(city.city)}`}
                    className="group rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-3 transition-all duration-200 hover:bg-zinc-800/70 hover:border-zinc-700"
                  >
                    <p className="text-sm font-medium text-zinc-200 group-hover:text-zinc-50 transition-colors truncate">
                      {city.city}
                    </p>
                    <p className="text-xs text-zinc-500 mt-0.5">
                      {city.state} &middot; {city.store_count} stores
                    </p>
                  </Link>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {/* Store Listing Section */}
      <section className="mx-auto max-w-7xl px-4 lg:px-6 py-8">
        <div className="mb-6">
          <h2 className="font-display text-xl font-semibold tracking-tight mb-1">
            {hasFilters ? "Search Results" : "All Stores"}
          </h2>
          <p className="text-sm text-zinc-500">
            {result.total.toLocaleString()} stores found
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

        <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-900/30">
          <StoreTable stores={result.stores} />
        </div>

        <Suspense fallback={null}>
          <Pagination
            page={result.page}
            pageSize={result.pageSize}
            total={result.total}
          />
        </Suspense>
      </section>

      {/* Browse by State -- always shown */}
      {states.length > 0 && (
        <section className="mx-auto max-w-7xl px-4 lg:px-6 pb-16">
          <div className="border-t border-zinc-800/60 pt-10">
            <h2 className="font-display text-lg font-semibold tracking-tight mb-4">
              Browse by State
            </h2>
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
              {states.map((s) => (
                <Link
                  key={s.slug}
                  href={`/stores/${s.slug}`}
                  className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors py-1"
                >
                  {abbreviationToStateName(s.state) ?? s.state}{" "}
                  <span className="text-zinc-600">({s.store_count})</span>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
