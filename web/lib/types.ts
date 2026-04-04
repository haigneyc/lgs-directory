/** TypeScript types mirroring the Python SQLAlchemy models and enums. */

// --- Enums (stored as varchar in Postgres) ---

export const STORE_STATUSES = [
  "candidate",
  "verified",
  "active",
  "unresponsive",
  "closed",
] as const;
export type StoreStatus = (typeof STORE_STATUSES)[number];

export const DISCOVERY_SOURCES = [
  "wpn",
  "google_places",
  "tcgplayer",
  "manual",
  "games_workshop",
  "comicbookstores",
  "league_comic_geeks",
  "video_game_sage",
] as const;
export type DiscoverySource = (typeof DISCOVERY_SOURCES)[number];

export const STORE_CATEGORIES = [
  "lgs",
  "comic_shop",
  "retro_games",
  "hobby_miniatures",
] as const;
export type StoreCategory = (typeof STORE_CATEGORIES)[number];

export const WPN_LEVELS = ["core", "premium"] as const;
export type WpnLevel = (typeof WPN_LEVELS)[number];

export const CHANNEL_TYPES = [
  "website",
  "tcgplayer",
  "ebay",
  "facebook",
  "other",
] as const;
export type ChannelType = (typeof CHANNEL_TYPES)[number];

export const PLATFORMS = [
  "crystal_commerce",
  "binderpos",
  "shopify",
  "squarespace",
  "woocommerce",
  "wordpress_stripe",
  "custom",
  "unknown",
] as const;
export type Platform = (typeof PLATFORMS)[number];

export const INVENTORY_SIZES = ["none", "small", "medium", "large"] as const;
export type InventorySize = (typeof INVENTORY_SIZES)[number];

export const PRICING_METHODS = ["manual", "synced", "unknown"] as const;
export type PricingMethod = (typeof PRICING_METHODS)[number];

export const PRESENCE_STATUSES = ["active", "unreachable", "dead"] as const;
export type PresenceStatus = (typeof PRESENCE_STATUSES)[number];

// --- Address (JSONB in Postgres) ---

export interface StoreAddress {
  street: string;
  city: string;
  state: string;
  zip_code: string;
}

// --- Row types ---

export interface Store {
  id: string;
  name: string;
  address: StoreAddress;
  latitude: number | null;
  longitude: number | null;
  phone: string | null;
  wpn_id: string | null;
  wpn_level: WpnLevel | null;
  google_place_id: string | null;
  status: StoreStatus;
  discovery_source: DiscoverySource;
  first_seen: string;
  last_validated: string | null;
  notes: string | null;
}

export interface OnlinePresence {
  id: string;
  store_id: string;
  channel_type: ChannelType;
  url: string;
  platform: Platform | null;
  sells_mtg_singles: boolean | null;
  estimated_inventory_size: InventorySize | null;
  pricing_method: PricingMethod | null;
  last_price_update_detected: string | null;
  http_status: number | null;
  last_checked: string | null;
  status: PresenceStatus;
}

export interface StoreWithDistance extends Store {
  distance_miles: number;
}

export interface StoreWithPresences extends Store {
  presences: OnlinePresence[];
}

export interface StateStats {
  state: string;
  slug: string;
  store_count: number;
  active_count: number;
  wpn_premium_count: number;
  online_count: number;
}

export interface CityStats {
  city: string;
  slug: string;
  store_count: number;
  active_count: number;
  wpn_premium_count: number;
  online_count: number;
}

export interface OnlineStore {
  store_id: string;
  store_name: string;
  presence_url: string;
  channel_type: ChannelType;
  platform: Platform | null;
  estimated_inventory_size: InventorySize | null;
}

export interface HoursPeriod {
  open: { day: number; hour: number; minute: number };
  close: { day: number; hour: number; minute: number };
}

export interface StoreEnrichment {
  hours_weekday_text: string[] | null;
  hours_periods: HoursPeriod[] | null;
  rating: number | null;
  user_rating_count: number | null;
  photo_refs: string[] | null;
  enriched_at: string | null;
}

export interface StoreContent {
  description: string | null;
  products: string[];
  has_events: boolean;
  event_url: string | null;
}
