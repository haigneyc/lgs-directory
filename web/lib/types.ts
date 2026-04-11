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

/** Premium listing status — null = unclaimed, 'claimed' = verified owner, 'premium' = paying subscriber */
export const PREMIUM_STATUSES = ["claimed", "premium"] as const;
export type PremiumStatus = (typeof PREMIUM_STATUSES)[number];

export interface Store {
  id: string;
  /**
   * Human-readable URL slug, e.g. ``darke-depths-gaming-dayton-oh``.
   * Backed by ``stores.slug`` (added in alembic c5e1a9f4b2d8). May be
   * null on rows that have not yet been backfilled; once the column is
   * promoted to NOT NULL post-backfill this can be tightened.
   */
  slug: string | null;
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
  /** Set on claim approval — email of the verified owner */
  claimed_by_email: string | null;
  /** When the claim was approved */
  claimed_at: string | null;
  /** null = unclaimed, 'claimed' = verified, 'premium' = paying */
  premium_status: PremiumStatus | null;
  /** Stripe subscription end date, set by webhook */
  premium_until: string | null;
  /** Hero banner image URL for premium stores */
  hero_image_url: string | null;
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
  store_slug: string | null;
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

/** Claim role options for the claim form */
export const CLAIM_ROLES = ["owner", "manager", "employee", "other"] as const;
export type ClaimRole = (typeof CLAIM_ROLES)[number];

/** Claim status lifecycle */
export const CLAIM_STATUSES = ["pending", "approved", "denied"] as const;
export type ClaimStatus = (typeof CLAIM_STATUSES)[number];

export interface StoreClaim {
  id: string;
  store_id: string;
  name: string;
  email: string;
  role: ClaimRole;
  proof_text: string;
  status: ClaimStatus;
  reviewed_at: string | null;
  created_at: string;
}

export interface StoreEvent {
  id: string;
  store_id: string;
  title: string;
  event_date: string;
  description: string | null;
  created_at: string;
}
