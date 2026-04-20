const FEATURED_CARD_COUNT = 8;
const GAME_CARD_COUNT = 8;
const STORE_TYPE_CARD_COUNT = 4;
const POPULAR_CITY_CARD_COUNT = 12;
const STATE_CITY_SKELETON_COUNT = 6;
const BROWSE_STATE_LINK_COUNT = 60;

const FEATURED_CARDS = Array.from(
  { length: FEATURED_CARD_COUNT },
  (_, index) => index
);
const GAME_CARDS = [0, 1, 2, 3, 4, 5, 6, 7] as const;
const STORE_TYPE_CARDS = [0, 1, 2, 3] as const;
const POPULAR_CITY_CARDS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11] as const;
const STATE_CITY_SKELETON_CARDS = Array.from(
  { length: STATE_CITY_SKELETON_COUNT },
  (_, index) => index
);
const HERO_STAT_LABEL_WIDTHS = ["w-16", "w-20", "w-24"] as const;
const FILTER_SELECT_WIDTHS = ["w-32", "w-36", "w-36", "w-40"] as const;
const BROWSE_STATE_LINK_WIDTHS = ["w-16", "w-20", "w-24", "w-28", "w-20", "w-24"] as const;

const BROWSE_STATE_LINKS = Array.from(
  { length: BROWSE_STATE_LINK_COUNT },
  (_, index) => index
);

function SectionHeadingSkeleton({
  titleWidthClass,
}: Readonly<{ titleWidthClass: string }>) {
  console.assert(typeof titleWidthClass === "string", "SectionHeadingSkeleton: titleWidthClass must be a string");
  console.assert(titleWidthClass.length > 0, "SectionHeadingSkeleton: titleWidthClass must not be empty");

  return (
    <div className="mb-6 flex items-center gap-3 animate-pulse">
      <div className="h-5 w-5 rounded bg-zinc-800" />
      <div className={`h-6 rounded bg-zinc-800 ${titleWidthClass}`} />
    </div>
  );
}

function BreadcrumbSkeleton({
  currentWidthClass,
  crumbCount = 2,
}: Readonly<{ currentWidthClass: string; crumbCount?: number }>) {
  console.assert(typeof currentWidthClass === "string", "BreadcrumbSkeleton: currentWidthClass must be a string");
  console.assert(currentWidthClass.length > 0, "BreadcrumbSkeleton: currentWidthClass must not be empty");
  console.assert(crumbCount >= 2 && crumbCount <= 4, "BreadcrumbSkeleton: crumbCount must stay bounded");

  return (
    <div className="flex items-center gap-2 animate-pulse">
      {Array.from({ length: crumbCount }, (_, index) => (
        <div key={index} className="flex items-center gap-2">
          {index > 0 && <div className="h-4 w-3 rounded bg-zinc-900/80" />}
          <div
            className={
              index === crumbCount - 1
                ? `h-4 rounded bg-zinc-800/70 ${currentWidthClass}`
                : "h-4 w-12 rounded bg-zinc-800/70"
            }
          />
        </div>
      ))}
    </div>
  );
}

export function HeroStatsSkeleton() {
  console.assert(HERO_STAT_LABEL_WIDTHS.length === 3, "HeroStatsSkeleton: expected three stat labels");
  console.assert(HERO_STAT_LABEL_WIDTHS[2] === "w-24", "HeroStatsSkeleton: expected categorized label width");

  return (
    <div
      aria-busy="true"
      aria-label="Loading hero stats"
      className="mt-12 flex flex-wrap items-center justify-center gap-6 text-center animate-pulse sm:gap-8"
    >
      {HERO_STAT_LABEL_WIDTHS.map((widthClass, index) => (
        <div key={widthClass} className="flex items-center gap-6">
          {index > 0 && <div className="hidden h-6 w-px bg-zinc-800 sm:block" />}
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 rounded bg-zinc-800/80" />
            <div className="h-7 w-14 rounded bg-zinc-800" />
            <div className={`h-4 rounded bg-zinc-800/70 ${widthClass}`} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function FeaturedStoresSkeleton() {
  console.assert(FEATURED_CARDS.length === FEATURED_CARD_COUNT, "FeaturedStoresSkeleton: card count mismatch");
  console.assert(FEATURED_CARD_COUNT <= 8, "FeaturedStoresSkeleton: card count must stay bounded");

  return (
    <section
      aria-busy="true"
      aria-label="Loading featured stores"
      className="mx-auto max-w-7xl px-4 py-12 lg:px-6"
    >
      <SectionHeadingSkeleton titleWidthClass="w-40" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURED_CARDS.map((card) => (
          <div
            key={card}
            className="overflow-hidden rounded-xl border border-yellow-500/20 bg-yellow-500/[0.03] animate-pulse"
          >
            <div className="h-36 bg-zinc-800/80" />
            <div className="space-y-2 p-4">
              <div className="h-4 w-3/4 rounded bg-zinc-800" />
              <div className="h-3 w-1/2 rounded bg-zinc-800/70" />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export function GameCategoryCardsSkeleton() {
  console.assert(GAME_CARDS.length === GAME_CARD_COUNT, "GameCategoryCardsSkeleton: card count mismatch");
  console.assert(GAME_CARD_COUNT % 4 === 0, "GameCategoryCardsSkeleton: expected four-column desktop grid");

  return (
    <section
      aria-busy="true"
      aria-label="Loading game categories"
      className="mx-auto max-w-7xl px-4 py-12 lg:px-6"
    >
      <SectionHeadingSkeleton titleWidthClass="w-40" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
        {GAME_CARDS.map((card) => (
          <div
            key={card}
            className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 animate-pulse"
          >
            <div className="mb-3 flex items-start justify-between">
              <div className="h-3 w-10 rounded bg-zinc-800/70" />
              <div className="h-3 w-20 rounded bg-zinc-800/50" />
            </div>
            <div className="h-4 w-5/6 rounded bg-zinc-800" />
          </div>
        ))}
      </div>
    </section>
  );
}

export function StoreTypeCardsSkeleton() {
  console.assert(STORE_TYPE_CARDS.length === STORE_TYPE_CARD_COUNT, "StoreTypeCardsSkeleton: card count mismatch");
  console.assert(STORE_TYPE_CARD_COUNT === 4, "StoreTypeCardsSkeleton: expected four store type cards");

  return (
    <section
      aria-busy="true"
      aria-label="Loading store types"
      className="mx-auto max-w-7xl px-4 pb-12 lg:px-6"
    >
      <SectionHeadingSkeleton titleWidthClass="w-32" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STORE_TYPE_CARDS.map((card) => (
          <div
            key={card}
            className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 animate-pulse"
          >
            <div className="mb-3 flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-yellow-600/10" />
              <div className="space-y-2">
                <div className="h-4 w-28 rounded bg-zinc-800" />
                <div className="h-3 w-20 rounded bg-zinc-800/70" />
              </div>
            </div>
            <div className="space-y-2">
              <div className="h-3 w-full rounded bg-zinc-800/70" />
              <div className="h-3 w-5/6 rounded bg-zinc-800/60" />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export function PopularCitiesSkeleton() {
  console.assert(POPULAR_CITY_CARDS.length === POPULAR_CITY_CARD_COUNT, "PopularCitiesSkeleton: card count mismatch");
  console.assert(POPULAR_CITY_CARD_COUNT % 6 === 0, "PopularCitiesSkeleton: expected six-column desktop grid");

  return (
    <section
      aria-busy="true"
      aria-label="Loading popular cities"
      className="mx-auto max-w-7xl px-4 pb-12 lg:px-6"
    >
      <SectionHeadingSkeleton titleWidthClass="w-36" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
        {POPULAR_CITY_CARDS.map((card) => (
          <div
            key={card}
            className="rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-3 animate-pulse"
          >
            <div className="h-4 w-4/5 rounded bg-zinc-800" />
            <div className="mt-2 h-3 w-3/4 rounded bg-zinc-800/70" />
          </div>
        ))}
      </div>
    </section>
  );
}

export function FilterBarSkeleton() {
  console.assert(FILTER_SELECT_WIDTHS.length === 4, "FilterBarSkeleton: expected four select placeholders");
  console.assert(
    FILTER_SELECT_WIDTHS.every((widthClass) => widthClass.startsWith("w-")),
    "FilterBarSkeleton: width classes must be tailwind width utilities"
  );

  return (
    <div
      aria-busy="true"
      aria-label="Loading filters"
      className="flex flex-wrap items-center gap-2.5 animate-pulse"
    >
      <div className="flex items-center gap-1.5">
        <div className="h-10 w-52 rounded-lg border border-zinc-800 bg-zinc-900/80" />
        <div className="h-10 w-10 rounded-lg border border-zinc-800 bg-zinc-900/80" />
      </div>
      {FILTER_SELECT_WIDTHS.map((widthClass, index) => (
        <div
          key={`${widthClass}-${index}`}
          className={`h-10 rounded-lg border border-zinc-800 bg-zinc-900/80 ${widthClass}`}
        />
      ))}
    </div>
  );
}

export function BrowseByStateSkeleton() {
  console.assert(BROWSE_STATE_LINKS.length === BROWSE_STATE_LINK_COUNT, "BrowseByStateSkeleton: link count mismatch");
  console.assert(BROWSE_STATE_LINK_COUNT % 6 === 0, "BrowseByStateSkeleton: expected evenly sized desktop rows");

  return (
    <section
      aria-busy="true"
      aria-label="Loading state links"
      className="mx-auto max-w-7xl px-4 pb-16 lg:px-6"
    >
      <div className="border-t border-zinc-800/60 pt-10">
        <div className="mb-4 h-6 w-36 rounded bg-zinc-800 animate-pulse" />
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6">
          {BROWSE_STATE_LINKS.map((link) => (
            <div
              key={link}
              className={`h-4 rounded bg-zinc-800/70 animate-pulse ${BROWSE_STATE_LINK_WIDTHS[link % BROWSE_STATE_LINK_WIDTHS.length]}`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

export function StateHeaderSkeleton() {
  console.assert(FEATURED_CARD_COUNT === 8, "StateHeaderSkeleton: shared card constant must remain stable");
  console.assert(FEATURED_CARD_COUNT > 0, "StateHeaderSkeleton: shared card constant must stay positive");

  return (
    <div
      aria-busy="true"
      aria-label="Loading state header"
      className="animate-pulse"
    >
      <BreadcrumbSkeleton currentWidthClass="w-20" />
      <div className="mb-6 mt-6">
        <div className="mb-2 flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-yellow-600/10" />
          <div className="h-8 w-72 max-w-full rounded bg-zinc-800" />
        </div>
      </div>
    </div>
  );
}

export function StateStatsSkeleton() {
  console.assert(
    STATE_CITY_SKELETON_CARDS.length === STATE_CITY_SKELETON_COUNT,
    "StateStatsSkeleton: city card count mismatch",
  );
  console.assert(
    STATE_CITY_SKELETON_COUNT >= 6 && STATE_CITY_SKELETON_COUNT <= 10,
    "StateStatsSkeleton: skeleton count must stay within the expected visual range",
  );

  return (
    <div
      aria-busy="true"
      aria-label="Loading state stats"
      className="animate-pulse"
    >
      <div className="mb-6 flex flex-wrap gap-4">
        <div className="h-9 w-28 rounded-lg border border-zinc-800 bg-zinc-900/50" />
        <div className="h-9 w-28 rounded-lg border border-zinc-800 bg-zinc-900/50" />
        <div className="h-9 w-36 rounded-lg border border-zinc-800 bg-zinc-900/50" />
        <div className="h-9 w-28 rounded-lg border border-zinc-800 bg-zinc-900/50" />
      </div>

      <div className="mb-8">
        <div className="mb-4 h-6 w-40 rounded bg-zinc-800" />
        <div className="min-h-[16rem] sm:min-h-[14rem] lg:min-h-[10rem]">
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {STATE_CITY_SKELETON_CARDS.map((card) => (
              <div
                key={card}
                className="rounded-xl border border-zinc-800 bg-zinc-900/50 px-4 py-3"
              >
                <div className="mb-2 h-4 w-3/4 rounded bg-zinc-800" />
                <div className="h-3 w-1/2 rounded bg-zinc-800/70" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function CityHeaderSkeleton() {
  console.assert(POPULAR_CITY_CARD_COUNT === 12, "CityHeaderSkeleton: shared card constant must remain stable");
  console.assert(POPULAR_CITY_CARD_COUNT > 0, "CityHeaderSkeleton: shared card constant must stay positive");

  return (
    <div
      aria-busy="true"
      aria-label="Loading city header"
      className="animate-pulse"
    >
      <BreadcrumbSkeleton currentWidthClass="w-24" crumbCount={3} />
      <div className="mb-6 mt-6">
        <div className="mb-1 h-8 w-80 max-w-full rounded bg-zinc-800" />
      </div>
    </div>
  );
}
