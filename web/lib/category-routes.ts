/**
 * Maps URL path segments to database category values and display metadata.
 */

export interface CategoryRoute {
  slug: string;           // URL path segment
  dbCategory: string;     // store_categories.category value
  label: string;          // Display name
  title: string;          // Page title
  description: string;    // Meta description
  heroText: string;       // Above-the-fold description
}

export const CATEGORY_ROUTES: CategoryRoute[] = [
  {
    slug: "comics",
    dbCategory: "comic_shop",
    label: "Comic Book Stores",
    title: "Comic Book Stores Near You | Roll For Store",
    description: "Find local comic book stores across the US. Browse new releases, back issues, graphic novels, and collectibles.",
    heroText: "Discover comic book stores in your area. From new releases to rare back issues, find the perfect shop for your collection.",
  },
  {
    slug: "retro-games",
    dbCategory: "retro_games",
    label: "Retro Video Game Stores",
    title: "Retro Video Game Stores Near You | Roll For Store",
    description: "Find retro video game stores across the US. Buy and sell classic consoles, cartridges, and vintage gaming collectibles.",
    heroText: "Hunt down retro video game stores near you. Classic consoles, rare cartridges, and everything vintage gaming.",
  },
  {
    slug: "warhammer",
    dbCategory: "hobby_miniatures",
    label: "Warhammer & Hobby Shops",
    title: "Warhammer & Hobby Shops Near You | Roll For Store",
    description: "Find Warhammer and miniatures hobby shops across the US. Games Workshop products, painting supplies, and tabletop wargaming.",
    heroText: "Find Warhammer and miniatures hobby shops near you. From Citadel paints to the latest army boxes, gear up for battle.",
  },
];

export function getCategoryRouteBySlug(slug: string): CategoryRoute | null {
  console.assert(typeof slug === "string", "getCategoryRouteBySlug: slug must be a string");
  const found = CATEGORY_ROUTES.find((r) => r.slug === slug);
  return found ?? null;
}

export function getCategoryRouteByDb(dbCategory: string): CategoryRoute | null {
  console.assert(typeof dbCategory === "string", "getCategoryRouteByDb: dbCategory must be a string");
  const found = CATEGORY_ROUTES.find((r) => r.dbCategory === dbCategory);
  return found ?? null;
}
