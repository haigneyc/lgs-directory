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
import { StoreTable } from "@/components/store-table";
import { FilterBar } from "@/components/filter-bar";
import { Pagination } from "@/components/pagination";
import { HeroSearch } from "@/components/hero-search";
import { AffiliateDisclosure } from "@/components/affiliate-disclosure";
import { AmazonShelf } from "@/components/amazon/amazon-shelf";
import { SHELVES } from "@/lib/amazon-shelves";
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
import { StoreTableSkeleton } from "@/components/store-table-skeleton";
import { ScrollToResults } from "@/components/scroll-to-results";

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

/**
 * Synchronous page shell — MUST NOT await anything (PERF-026).
 *
 * Behavior note: prior to this refactor, the hero / category cards /
 * popular cities sections were hidden when the user applied a filter
 * (`?category=...`, `?state=...`, etc.). That condition required
 * awaiting searchParams at the top level, which opted the entire
 * route into dynamic rendering and blocked the edge cache. The hero
 * is now rendered unconditionally so the shell can prerender. The
 * dynamic store listing below still respects all searchParams.
 */
export default function HomePage({ searchParams }: PageProps) {
  console.assert(GAME_CATEGORIES.length === GAME_CATEGORIES_LENGTH, "HomePage: GAME_CATEGORIES count mismatch");
  console.assert(STORE_TYPES.length === STORE_TYPES_LENGTH, "HomePage: STORE_TYPES count mismatch");
  console.assert(typeof searchParams === "object", "HomePage: searchParams must be an object (Promise)");

  return (
    <div>
      {/* Hero Section -- always rendered so the shell prerenders */}
      <section className="relative overflow-hidden border-b border-amber-900/20 parchment-texture">
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

            <HeroSearch />
          </div>

          <Suspense fallback={null}>
            <HeroStatsBlock />
          </Suspense>
        </div>
      </section>

      <Suspense fallback={null}>
        <GameCategoryCards />
      </Suspense>

      {/* eBay Storefront Banner -- static */}
      <section className="mx-auto max-w-7xl px-4 lg:px-6 pb-4 pt-4">
        <a
          href="https://www.ebay.com/inf/rollforstore"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between gap-4 rounded-xl border border-yellow-600/30 bg-yellow-600/5 px-5 py-4 hover:bg-yellow-600/10 hover:border-yellow-500/50 transition-all duration-200 group"
        >
          <div className="flex items-center gap-3">
            <span className="text-yellow-500 text-xl">🃏</span>
            <div>
              <p className="text-sm font-semibold text-yellow-400 group-hover:text-yellow-300 transition-colors">
                Shop Trading Cards on eBay
              </p>
              <p className="text-xs text-zinc-500">
                Browse MTG, Pokemon, Yu-Gi-Oh &amp; more at the Roll For Store eBay storefront
              </p>
            </div>
          </div>
          <span className="text-xs font-medium text-yellow-600 group-hover:text-yellow-500 transition-colors whitespace-nowrap">
            Shop Now →
          </span>
        </a>
        <AffiliateDisclosure className="mt-1.5 px-1" />
      </section>

      <Suspense fallback={null}>
        <StoreTypeCards />
      </Suspense>

      <Suspense fallback={null}>
        <PopularCitiesBlock />
      </Suspense>

      {/* Store Listing Section — dynamic, awaits searchParams */}
      <section id="results" className="mx-auto max-w-7xl px-4 lg:px-6 py-8">
        <Suspense fallback={null}>
          <ScrollToResults />
        </Suspense>
        <Suspense fallback={null}>
          <FilterBarWrapper />
        </Suspense>

        <Suspense fallback={<StoreTableSkeleton />}>
          <DynamicStoreListing searchParams={searchParams} />
        </Suspense>
      </section>

      {/* Amazon affiliate shelf — broad TCG audience default. */}
      <section className="mx-auto max-w-7xl px-4 lg:px-6 pb-12">
        <AmazonShelf shelf={SHELVES["tcg-essentials"]} compact />
      </section>

      <Suspense fallback={null}>
        <BrowseByStateBlock />
      </Suspense>
    </div>
  );
}

/**
 * Hero stats row — fetches aggregate counts. Does NOT depend on
 * searchParams, so it prerenders at build time.
 */
async function HeroStatsBlock() {
  const [totalCount, categoryStats, states] = await Promise.all([
    getTotalStoreCount(),
    getCategoryStats(),
    getStateIndex(),
  ]);

  let categorizedTotal = 0;
  const catLimit = Math.min(categoryStats.length, 20);
  for (let i = 0; i < catLimit; i++) {
    categorizedTotal += categoryStats[i].count;
  }

  const includesDC = states.some((s) => s.state === "DC");
  const usStateCount = includesDC ? states.length - 1 : states.length;

  return (
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
  );
}

async function GameCategoryCards() {
  const gameTags = await getGameTagCounts();
  const tagCountMap = new Map<string, number>();
  const tagLimit = Math.min(gameTags.length, 100);
  for (let i = 0; i < tagLimit; i++) {
    tagCountMap.set(gameTags[i].tag, gameTags[i].count);
  }

  return (
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
              href={`/?game=${encodeURIComponent(game.key)}`}
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
  );
}

async function StoreTypeCards() {
  const categoryStats = await getCategoryStats();
  const categoryCountMap = new Map<string, number>();
  const catLimit = Math.min(categoryStats.length, 20);
  for (let i = 0; i < catLimit; i++) {
    categoryCountMap.set(categoryStats[i].category, categoryStats[i].count);
  }

  return (
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
  );
}

async function PopularCitiesBlock() {
  const popularCities = await getPopularCities(12);
  console.assert(Array.isArray(popularCities), "PopularCitiesBlock: popularCities must be an array");
  if (popularCities.length === 0) {
    return null;
  }

  return (
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
  );
}

async function FilterBarWrapper() {
  const filterOptions = await getFilterOptions();
  return (
    <FilterBar
      states={filterOptions.states}
      statuses={filterOptions.statuses}
      wpnLevels={filterOptions.wpnLevels}
      categories={filterOptions.categories}
    />
  );
}

async function BrowseByStateBlock() {
  const states = await getStateIndex();
  if (states.length === 0) {
    return null;
  }
  return (
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
  );
}

/**
 * Dynamic store listing — awaits searchParams. Only this block streams
 * in per-request; everything above is prerendered and cached.
 */
async function DynamicStoreListing({
  searchParams,
}: Readonly<{
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}>) {
  const params = await searchParams;
  console.assert(typeof params === "object", "DynamicStoreListing: params must be an object");

  const hasFilters = typeof params.page === "string" ||
    typeof params.state === "string" ||
    typeof params.status === "string" ||
    typeof params.wpn === "string" ||
    typeof params.q === "string" ||
    typeof params.category === "string" ||
    typeof params.game === "string";

  const rawPage =
    typeof params.page === "string" ? parseInt(params.page, 10) : 1;
  const state = typeof params.state === "string" ? params.state : undefined;
  const status = typeof params.status === "string" ? params.status : undefined;
  const wpnLevel = typeof params.wpn === "string" ? params.wpn : undefined;
  const search = typeof params.q === "string" ? params.q : undefined;
  const category = typeof params.category === "string" ? params.category : undefined;
  const game = typeof params.game === "string" ? params.game : undefined;

  const initialResult = await listStores({
    page: rawPage,
    state,
    status,
    wpnLevel,
    search,
    category,
    game,
  });

  const totalPages =
    Math.ceil(initialResult.total / initialResult.pageSize) || 1;
  const safePage = Math.min(Math.max(1, rawPage), totalPages);

  const result =
    safePage === rawPage
      ? initialResult
      : await listStores({ page: safePage, state, status, wpnLevel, search, category, game });

  return (
    <>
      <div className="mb-6">
        <h2 className="font-display text-xl font-semibold tracking-tight mb-1">
          {hasFilters ? "Search Results" : "All Stores"}
        </h2>
        <p className="text-sm text-zinc-500">
          {result.total.toLocaleString()} stores found
        </p>
      </div>

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
    </>
  );
}
