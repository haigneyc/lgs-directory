/**
 * Pure helpers for building per-store `<title>` and `<meta name="description">`
 * content. These functions take plain data and return plain strings so they
 * are trivially unit-testable (no DB, no Next.js, no React).
 *
 * Motivation: rollforstore.com GSC on 2026-04-07 showed 4,005 impressions /
 * 12 clicks (0.30% CTR) at avg position ~13 across per-store pages. Rankings
 * are fine; the snippets aren't converting. Template metadata was being
 * emitted for every store; this module produces distinct, category-aware,
 * city/state-aware copy for each listing.
 *
 * Title target (<60 chars):
 *   "Store Name — TCG store in City, ST"
 * Description target (150-160 chars):
 *   "Name in City, ST — local game store for Magic, Pokémon & Warhammer.
 *    Open Tue-Sat. See hours, address & events on Roll For Store."
 */

import type { StoreCategory } from "./types";

/**
 * Google desktop snippet typically truncates around 155-160 characters.
 * We target 150-160 and clamp hard at 160 with an ellipsis to avoid
 * mid-word cuts.
 */
export const META_DESCRIPTION_MIN = 150;
export const META_DESCRIPTION_MAX = 160;

/** Google truncates SERP titles around ~60 chars; we clamp at 60. */
export const META_TITLE_MAX = 60;

/**
 * Primary store category derived from the categories array. The page's
 * primary category is the first row returned by `getStoreCategories`
 * (ordered by insertion today, which tracks Dash's discovery order).
 * When no category is known we fall back to "lgs" labelling as
 * "local game store" per Vera's v2 brief (never emit "unknown").
 */
export type PrimaryCategoryLabel =
  | "TCG"
  | "Comic"
  | "Retro game"
  | "Warhammer"
  | "Game";

const CATEGORY_LABELS: Record<StoreCategory, PrimaryCategoryLabel> = {
  lgs: "TCG",
  comic_shop: "Comic",
  retro_games: "Retro game",
  hobby_miniatures: "Warhammer",
};

/**
 * Pick the short category label used in the title slot. When there are
 * no known categories we return "Game" so the title reads
 * "... Game store in City, ST" (rather than "undefined store").
 */
export function primaryCategoryLabel(
  categories: readonly StoreCategory[]
): PrimaryCategoryLabel {
  console.assert(
    Array.isArray(categories),
    "primaryCategoryLabel: categories must be an array"
  );
  console.assert(
    categories.length >= 0,
    "primaryCategoryLabel: categories length must be non-negative"
  );
  if (categories.length === 0) {
    return "Game";
  }
  const first = categories[0];
  const label = CATEGORY_LABELS[first];
  return label ?? "Game";
}

/**
 * Longer descriptor used in the meta description body. Mirrors the
 * short label but reads naturally in prose.
 */
function descriptiveCategoryPhrase(
  categories: readonly StoreCategory[]
): string {
  console.assert(
    Array.isArray(categories),
    "descriptiveCategoryPhrase: categories must be an array"
  );
  if (categories.length === 0) {
    return "local game store";
  }
  const first = categories[0];
  if (first === "lgs") return "local game store for Magic, Pokémon & board games";
  if (first === "comic_shop") return "local comic shop with new releases & back issues";
  if (first === "retro_games") return "retro video game store for classic consoles & cartridges";
  if (first === "hobby_miniatures") return "Warhammer & miniatures hobby shop";
  return "local game store";
}

/**
 * Summarise weekday_text into a compact "Open D1-D2" clause, or return
 * null if we cannot derive one. Examples of inputs from Google Places:
 *   ["Monday: 12:00 – 8:00 PM", "Tuesday: 12:00 – 8:00 PM", ..., "Sunday: Closed"]
 * We look for the longest contiguous run of open days and express it
 * as "Open Mon-Sat". If only a single day is open we write "Open Tue".
 * If the store is closed every day or the input is malformed we return
 * null so the caller can omit the clause entirely.
 */
const DAY_ORDER = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
] as const;
const DAY_ABBREV: Record<(typeof DAY_ORDER)[number], string> = {
  Monday: "Mon",
  Tuesday: "Tue",
  Wednesday: "Wed",
  Thursday: "Thu",
  Friday: "Fri",
  Saturday: "Sat",
  Sunday: "Sun",
};

export function summarizeHours(
  weekdayText: readonly string[] | null | undefined
): string | null {
  console.assert(
    weekdayText === null ||
      weekdayText === undefined ||
      Array.isArray(weekdayText),
    "summarizeHours: weekdayText must be null/undefined/array"
  );
  if (!weekdayText || weekdayText.length === 0) {
    return null;
  }

  // Map "Monday: 12:00 - 8:00 PM" -> open=true; "Sunday: Closed" -> false.
  const open: boolean[] = new Array(DAY_ORDER.length).fill(false);
  const dayCount = Math.min(weekdayText.length, 14);
  for (let i = 0; i < dayCount; i++) {
    const line = weekdayText[i];
    if (typeof line !== "string") continue;
    const lower = line.toLowerCase();
    const dayIdx = DAY_ORDER.findIndex((d) => lower.startsWith(d.toLowerCase()));
    if (dayIdx < 0) continue;
    const isClosed = lower.includes("closed");
    open[dayIdx] = !isClosed;
  }

  // Find the longest contiguous run of open days.
  let bestStart = -1;
  let bestLen = 0;
  let curStart = -1;
  let curLen = 0;
  const loopCap = DAY_ORDER.length;
  for (let i = 0; i < loopCap; i++) {
    if (open[i]) {
      if (curStart < 0) curStart = i;
      curLen += 1;
      if (curLen > bestLen) {
        bestLen = curLen;
        bestStart = curStart;
      }
    } else {
      curStart = -1;
      curLen = 0;
    }
  }

  if (bestLen === 0 || bestStart < 0) return null;

  if (bestLen === 1) {
    return `Open ${DAY_ABBREV[DAY_ORDER[bestStart]]}`;
  }
  if (bestLen === 7) {
    return "Open daily";
  }
  const start = DAY_ABBREV[DAY_ORDER[bestStart]];
  const end = DAY_ABBREV[DAY_ORDER[bestStart + bestLen - 1]];
  return `Open ${start}-${end}`;
}

/** Normalize whitespace + trim for safe string comparison. */
function norm(s: string): string {
  return s.toLowerCase().replace(/\s+/g, " ").trim();
}

export interface DescriptionInput {
  name: string;
  city: string;
  state: string;
  categories: readonly StoreCategory[];
  weekdayText: readonly string[] | null;
  hasEvents: boolean;
}

/**
 * Build the per-store meta description string.
 *
 * Structure:
 *   "<Name prefix> — <category phrase>. [<hours clause>.] See hours,
 *    address [& events] on Roll For Store."
 *
 * - If the store name already contains the city, don't repeat it in the
 *   "in City, ST" suffix.
 * - If categories are empty, use "local game store".
 * - If weekdayText is null/empty, omit the hours clause entirely.
 * - If hasEvents is true, add "& events" to the tail clause.
 *
 * Output is clamped to META_DESCRIPTION_MAX characters.
 */
export function buildStoreMetaDescription(input: DescriptionInput): string {
  console.assert(
    typeof input.name === "string" && input.name.length > 0,
    "buildStoreMetaDescription: name required"
  );
  console.assert(
    typeof input.city === "string" && input.city.length > 0,
    "buildStoreMetaDescription: city required"
  );
  console.assert(
    typeof input.state === "string" && input.state.length > 0,
    "buildStoreMetaDescription: state required"
  );

  const nameHasCity = norm(input.name).includes(norm(input.city));
  const prefix = nameHasCity
    ? `${input.name}, ${input.state}`
    : `${input.name} in ${input.city}, ${input.state}`;

  const phrase = descriptiveCategoryPhrase(input.categories);
  const hoursClause = summarizeHours(input.weekdayText);
  const eventsFragment = input.hasEvents ? " & events" : "";

  // Assemble candidate sentence. Prefer the hours clause; drop it if we
  // would exceed the 160-char cap.
  const tail = ` See hours, address${eventsFragment} on Roll For Store.`;
  const base = `${prefix} — ${phrase}.`;

  let candidate: string;
  if (hoursClause !== null) {
    candidate = `${base} ${hoursClause}.${tail}`;
    if (candidate.length <= META_DESCRIPTION_MAX) {
      return candidate;
    }
  }
  candidate = `${base}${tail}`;
  if (candidate.length <= META_DESCRIPTION_MAX) {
    return candidate;
  }
  // Last resort: truncate at max with ellipsis.
  return `${candidate.slice(0, META_DESCRIPTION_MAX - 1).trimEnd()}…`;
}

export interface TitleInput {
  name: string;
  city: string;
  state: string;
  categories: readonly StoreCategory[];
}

/**
 * Build the per-store `<title>` string.
 *
 * Format: `"<Name> — <Category> store in <City>, <ST>"`
 *
 * If the full form exceeds META_TITLE_MAX we first drop the " in City, ST"
 * clause when the name already contains the city, then fall back to
 * truncating the name with an ellipsis.
 */
export function buildStoreTitle(input: TitleInput): string {
  console.assert(
    typeof input.name === "string" && input.name.length > 0,
    "buildStoreTitle: name required"
  );
  console.assert(
    typeof input.city === "string" && input.city.length > 0,
    "buildStoreTitle: city required"
  );
  console.assert(
    typeof input.state === "string" && input.state.length > 0,
    "buildStoreTitle: state required"
  );

  const label = primaryCategoryLabel(input.categories);
  const nameHasCity = norm(input.name).includes(norm(input.city));

  const full = nameHasCity
    ? `${input.name} — ${label} store in ${input.state}`
    : `${input.name} — ${label} store in ${input.city}, ${input.state}`;

  if (full.length <= META_TITLE_MAX) {
    return full;
  }

  // Try the compact form (drop city) even if name doesn't contain it.
  const compact = `${input.name} — ${label} store in ${input.state}`;
  if (compact.length <= META_TITLE_MAX) {
    return compact;
  }

  // Truncate the name portion.
  const suffix = ` — ${label} store`;
  const room = META_TITLE_MAX - suffix.length - 1;
  if (room <= 1) {
    return input.name.slice(0, META_TITLE_MAX);
  }
  return `${input.name.slice(0, room).trimEnd()}…${suffix}`;
}
