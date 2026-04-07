/**
 * Curated Amazon affiliate "shelves" — small lists of high-intent product
 * searches grouped by audience category.
 *
 * IMPORTANT: every entry uses an Amazon SEARCH query (not a hard-coded ASIN)
 * so the link target stays valid even when individual products are
 * discontinued or restocked.
 */

export type ShelfId =
  | "tcg-essentials"
  | "warhammer-hobby"
  | "retro-games"
  | "comics-storage";

export interface ShelfLink {
  /** What the user sees as the link label. */
  title: string;
  /** Free-form Amazon search query passed to buildAmazonSearchLink. */
  query: string;
  /** One-line description shown beneath the link. */
  blurb: string;
}

export interface ShelfDefinition {
  id: ShelfId;
  /** Card heading shown to users. */
  title: string;
  /** Short intro line shown under the heading. */
  intro: string;
  links: ShelfLink[];
}

const TCG_ESSENTIALS: ShelfDefinition = {
  id: "tcg-essentials",
  title: "TCG Player Essentials",
  intro: "Sleeves, deck boxes, and table gear most local game store regulars keep on hand.",
  links: [
    { title: "Card Sleeves (Standard)", query: "trading card sleeves standard size", blurb: "Matte and clear sleeves for MTG, Pokemon, and most TCGs." },
    { title: "Deck Boxes", query: "trading card deck box", blurb: "Hard-shell and leatherette boxes that fit a sleeved 60+ card deck." },
    { title: "Playmats", query: "tcg playmat 24x14", blurb: "Stitched-edge playmats sized for tournament play." },
    { title: "Spindown & Polyhedral Dice", query: "spindown d20 dice mtg", blurb: "Life counters and full poly sets for table play." },
    { title: "Card Binders (Side-Loading)", query: "card binder side loading 9 pocket", blurb: "Protect singles in zip-up 9-pocket binders." },
    { title: "Top Loaders", query: "card top loaders 3x4", blurb: "Rigid 3x4 holders for valuable singles." },
    { title: "Deck Cases (Multi-Deck)", query: "tcg multi deck case storage", blurb: "Bring four to eight sleeved decks to game night." },
    { title: "Card Storage Boxes", query: "trading card storage box", blurb: "Long boxes and 800-count cardboard storage." },
  ],
};

const WARHAMMER_HOBBY: ShelfDefinition = {
  id: "warhammer-hobby",
  title: "Warhammer Painter's Bench",
  intro: "Tools and consumables for Warhammer, AoS, and miniature painting hobbyists.",
  links: [
    { title: "Citadel Paint Sets", query: "citadel paint set", blurb: "Games Workshop's official paint pots and starter sets." },
    { title: "Miniature Brushes", query: "miniature painting brush set", blurb: "Fine-tip synthetic and Kolinsky brushes for detail work." },
    { title: "Basing Materials", query: "miniature basing flock sand", blurb: "Static grass, flock, and sand for finishing bases." },
    { title: "Self-Healing Cutting Mat", query: "self healing cutting mat a3", blurb: "Protects your desk while clipping sprues." },
    { title: "Primer Spray (Matte)", query: "matte primer spray miniatures", blurb: "Plastic-safe matte primer in black, white, and grey." },
    { title: "Hobby Knives & Blades", query: "hobby knife replacement blades", blurb: "Sharp craft knives and replacement blade packs." },
    { title: "Plastic Glue", query: "plastic model cement glue", blurb: "Polystyrene cement for assembling Citadel kits." },
    { title: "Sprue Cutters", query: "miniature sprue cutters flush", blurb: "Flush cutters for clean part removal." },
  ],
};

const RETRO_GAMES: ShelfDefinition = {
  id: "retro-games",
  title: "Retro Gaming Gear",
  intro: "Maintenance and quality-of-life upgrades for vintage console collectors.",
  links: [
    { title: "Cartridge Cleaning Kits", query: "retro game cartridge cleaning kit", blurb: "Bring grimy NES, SNES, and Genesis carts back to life." },
    { title: "Replacement Controllers", query: "retro console replacement controller", blurb: "OEM-style pads for classic consoles." },
    { title: "RetroTink Upscaler", query: "retrotink upscaler", blurb: "Lag-free analog-to-HDMI upscaling for CRT-era consoles." },
    { title: "Cartridge Storage Cases", query: "video game cartridge storage case", blurb: "Protective cases for loose carts." },
    { title: "Screen Cleaning Kit", query: "crt screen cleaner kit", blurb: "Safe cleaners for CRTs, LCDs, and handheld screens." },
    { title: "HDMI Adapters (Retro)", query: "retro console hdmi adapter", blurb: "HDMI converters for N64, GameCube, and similar." },
    { title: "Game Boy Replacement Shells", query: "game boy replacement shell", blurb: "Restore beat-up handhelds with new shells and buttons." },
  ],
};

const COMICS_STORAGE: ShelfDefinition = {
  id: "comics-storage",
  title: "Comic Collector Storage",
  intro: "Boxes, bags, and boards to keep your single issues collection-grade.",
  links: [
    { title: "Long Boxes", query: "comic book long box", blurb: "Standard cardboard long boxes (~300 count)." },
    { title: "Short Boxes", query: "comic book short box", blurb: "Easier-to-lift short boxes for active reading piles." },
    { title: "Bags & Boards (Current Size)", query: "current size comic bags and boards", blurb: "Acid-free bags and backer boards for modern issues." },
    { title: "Bags & Boards (Silver Age)", query: "silver age comic bags and boards", blurb: "Sized for older Silver and Bronze Age issues." },
    { title: "Mylar Sleeves", query: "mylar comic sleeves", blurb: "Archival mylar for keys and high-grade books." },
    { title: "Magazine Bags", query: "magazine size comic bags", blurb: "For oversized issues, treasury editions, and magazines." },
    { title: "Comic Dividers", query: "comic book box dividers", blurb: "Tabbed dividers to organize a long box by series." },
  ],
};

export const SHELVES: Record<ShelfId, ShelfDefinition> = {
  "tcg-essentials": TCG_ESSENTIALS,
  "warhammer-hobby": WARHAMMER_HOBBY,
  "retro-games": RETRO_GAMES,
  "comics-storage": COMICS_STORAGE,
};

/**
 * Map an internal store category (matches `store_categories.category`)
 * to the most relevant shelf for a "while you're here" recommendation.
 */
export function shelfForStoreCategory(dbCategory: string | null): ShelfDefinition {
  console.assert(
    dbCategory === null || typeof dbCategory === "string",
    "shelfForStoreCategory: dbCategory must be a string or null"
  );

  if (dbCategory === "comic_shop") {
    return SHELVES["comics-storage"];
  }
  if (dbCategory === "retro_games") {
    return SHELVES["retro-games"];
  }
  if (dbCategory === "hobby_miniatures") {
    return SHELVES["warhammer-hobby"];
  }
  return SHELVES["tcg-essentials"];
}
