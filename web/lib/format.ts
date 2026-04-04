import type { StoreAddress, Platform } from "./types";

const PRODUCT_LABELS: Record<string, string> = {
  mtg: "Magic: The Gathering",
  pokemon: "Pokemon TCG",
  yugioh: "Yu-Gi-Oh!",
  fab: "Flesh and Blood",
  board_games: "Board Games",
  dnd: "D&D / RPGs",
  miniatures: "Miniatures",
  comics: "Comics",
};

export function formatProduct(key: string): string {
  console.assert(
    typeof key === "string",
    "formatProduct: key must be a string"
  );
  console.assert(
    key.length > 0,
    "formatProduct: key must not be empty"
  );
  return PRODUCT_LABELS[key] ?? key;
}

export function formatAddress(addr: StoreAddress): string {
  return `${addr.street}, ${addr.city}, ${addr.state} ${addr.zip_code}`;
}

export function formatCityState(addr: StoreAddress): string {
  return `${addr.city}, ${addr.state}`;
}

export function formatPlatform(p: Platform): string {
  const map: Record<Platform, string> = {
    crystal_commerce: "CrystalCommerce",
    binderpos: "BinderPOS",
    shopify: "Shopify",
    squarespace: "Squarespace",
    woocommerce: "WooCommerce",
    wordpress_stripe: "WordPress + Stripe",
    custom: "Custom",
    unknown: "Unknown",
  };
  return map[p] ?? p;
}

export function formatDistance(miles: number): string {
  if (miles < 1) {
    return `${(miles * 5280).toFixed(0)} ft`;
  }
  return `${miles.toFixed(1)} mi`;
}

export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function formatRating(rating: number, count: number): string {
  console.assert(
    typeof rating === "number",
    "formatRating: rating must be a number"
  );
  console.assert(
    typeof count === "number",
    "formatRating: count must be a number"
  );
  return `\u2605 ${rating.toFixed(1)} (${count})`;
}

const CATEGORY_LABELS: Record<string, string> = {
  lgs: "Local Game Store",
  comic_shop: "Comic Book Store",
  retro_games: "Retro Video Game Store",
  hobby_miniatures: "Warhammer & Hobby Shop",
};

export function formatCategory(key: string): string {
  console.assert(typeof key === "string", "formatCategory: key must be a string");
  console.assert(key.length > 0, "formatCategory: key must not be empty");
  return CATEGORY_LABELS[key] ?? key;
}

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  lgs: "Local game stores selling Magic: The Gathering, Pokemon, board games, and more.",
  comic_shop: "Comic book stores carrying new releases, back issues, graphic novels, and collectibles.",
  retro_games: "Retro video game stores specializing in classic consoles, cartridges, and vintage gaming.",
  hobby_miniatures: "Warhammer, miniatures, and hobby shops for tabletop wargaming enthusiasts.",
};

export function getCategoryDescription(key: string): string {
  console.assert(typeof key === "string", "getCategoryDescription: key must be a string");
  return CATEGORY_DESCRIPTIONS[key] ?? "";
}
