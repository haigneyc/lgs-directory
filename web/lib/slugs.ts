export const MAX_SLUG_LENGTH = 100;

/**
 * Hard upper bound on a store slug. Mirrors the
 * ``stores.slug VARCHAR(160)`` column added in migration c5e1a9f4b2d8.
 */
export const MAX_STORE_SLUG_LENGTH = 160;

/**
 * RFC 4122 UUID v1-v5 format check. Used to detect when an old
 * ``/store/<uuid>`` URL has been requested so we can 301-redirect it
 * to the canonical slug URL.
 */
const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function isUuid(value: string): boolean {
  console.assert(typeof value === "string", "isUuid: value must be a string");
  console.assert(value.length >= 0, "isUuid: value length must be non-negative");
  return UUID_REGEX.test(value);
}

/**
 * Quote characters (straight + curly, single + double) that must be
 * stripped ENTIRELY before slugification, so that "Jan's" becomes
 * "jans" rather than "jan-s". Must stay in sync with the equivalent
 * constant in ``scripts/backfill_store_slugs.py``.
 */
const QUOTE_CHARS_REGEX = /['\u2018\u2019\u201B\u201C\u201D\u201F"]/g;

/**
 * Trailing legal-entity tokens that should be stripped from a store
 * name before slugification. Matched case-insensitively, only at the
 * end of the string, optionally preceded by a comma and whitespace.
 * Must stay in sync with ``_LEGAL_SUFFIX_REGEX`` in
 * ``scripts/backfill_store_slugs.py``.
 *
 * Worked examples (see also _slugify in the python script):
 *   "Jan's Tropical Fish"        -> "jans-tropical-fish"
 *   "Bob's Tropical Fish"        -> "bobs-tropical-fish"
 *   "Starjumpers Tank LLC"       -> "starjumpers-tank"
 *   "Pam's Pets & Fish"          -> "pams-pets-fish"
 *   "Aqua Cave Inc."             -> "aqua-cave"
 *   "Fish R Us, Co."             -> "fish-r-us"
 *   "A-Z Aquatic LLC"            -> "a-z-aquatic"
 *   "The Fish People"            -> "the-fish-people"
 *   "Co Company Stores"          -> "co-company-stores" (mid-name, not stripped)
 */
const LEGAL_SUFFIX_REGEX =
  /[,\s]+(l\.?l\.?c\.?|inc\.?|incorporated|corp\.?|corporation|ltd\.?|limited|co\.?|company)\s*$/i;

function stripLegalSuffix(name: string): string {
  console.assert(typeof name === "string", "stripLegalSuffix: name must be a string");
  // Apply repeatedly so "Foo Inc, LLC" loses both tokens.
  let prev = name;
  let next = name.replace(LEGAL_SUFFIX_REGEX, "");
  for (let i = 0; i < 4 && next !== prev; i++) {
    prev = next;
    next = next.replace(LEGAL_SUFFIX_REGEX, "");
  }
  // If the entire name was a legal token, fall back to the original.
  return next.trim().length > 0 ? next.trim() : name.trim();
}

/**
 * Run the standard slugify pipeline on a single string component.
 * Lowercases, strips quotes entirely, then maps anything outside
 * ``[a-z0-9 -]`` to a space, collapses whitespace and dash runs, and
 * trims leading/trailing dashes. Mirrors ``_slug_part`` in
 * ``scripts/backfill_store_slugs.py``.
 */
function slugifyPart(value: string): string {
  console.assert(typeof value === "string", "slugifyPart: value must be a string");
  const result = value
    .toLowerCase()
    .replace(QUOTE_CHARS_REGEX, "")
    .replace(/[^a-z0-9 -]/g, " ")
    .trim()
    .replace(/\s+/g, "-")
    .replace(/-{2,}/g, "-")
    .replace(/^-|-$/g, "");
  console.assert(!result.includes("--"), "slugifyPart: result must not contain double hyphens");
  return result;
}

/**
 * Build a store slug of the form
 * ``<store-name>-<city>-<state-abbr-lower>``. Pure ASCII, kebab-case,
 * collapsed dashes, trimmed to ``MAX_STORE_SLUG_LENGTH``.
 *
 * Pre-processing (must stay in lockstep with the python backfill):
 *   1. Strip trailing legal-entity tokens from the store name only
 *      (LLC, Inc, Corp, Ltd, Co, Company, etc.).
 *   2. Strip ALL quote characters entirely so "Jan's" -> "jans".
 *   3. Then run the standard non-alphanumeric -> hyphen pass.
 *
 * Backfill collision handling (e.g. two stores with identical name +
 * city) is the caller's responsibility -- typically by appending a
 * short suffix derived from the UUID. See
 * ``scripts/backfill_store_slugs.py``.
 */
export function buildStoreSlug(
  storeName: string,
  city: string,
  stateAbbrev: string
): string {
  console.assert(typeof storeName === "string" && storeName.length > 0, "buildStoreSlug: storeName must be non-empty");
  console.assert(typeof city === "string", "buildStoreSlug: city must be a string");
  console.assert(typeof stateAbbrev === "string", "buildStoreSlug: stateAbbrev must be a string");

  const cleanedName = stripLegalSuffix(storeName);
  console.assert(cleanedName.length > 0, "buildStoreSlug: cleanedName must be non-empty");

  const nameSlug = slugifyPart(cleanedName);
  const citySlug = slugifyPart(city);
  const stateSlug = slugifyPart(stateAbbrev);
  console.assert(nameSlug.length > 0, "buildStoreSlug: nameSlug must be non-empty");

  // De-duplicate the city when the store name already ends with it.
  // Match on the SLUG forms (full suffix only) so partial-word matches
  // like "Game Stop" / "Gamestown" do NOT trigger dedup. Check the
  // longer "-city-state" suffix BEFORE "-city" so names like
  // "Game X Change Gainesville TX" in Gainesville, TX emit as-is
  // rather than appending "-tx" twice.
  const hasCity = citySlug.length > 0;
  const hasState = stateSlug.length > 0;
  const cityStateSuffix = "-" + citySlug + "-" + stateSlug;
  const cityStateWhole = citySlug + "-" + stateSlug;
  const citySuffix = "-" + citySlug;
  const nameEndsWithCityState =
    hasCity &&
    hasState &&
    (nameSlug === cityStateWhole || nameSlug.endsWith(cityStateSuffix));
  const nameEndsWithCity =
    hasCity && (nameSlug === citySlug || nameSlug.endsWith(citySuffix));

  const segments: string[] = [nameSlug];
  if (nameEndsWithCityState) {
    // Name already contains "-city-state"; emit name as-is (no city, no state).
  } else {
    if (hasCity && !nameEndsWithCity) {
      segments.push(citySlug);
    }
    if (hasState) {
      segments.push(stateSlug);
    }
  }

  const ascii = segments
    .filter((s) => s.length > 0)
    .join("-")
    .replace(/-{2,}/g, "-")
    .replace(/^-|-$/g, "");

  const truncated =
    ascii.length > MAX_STORE_SLUG_LENGTH
      ? ascii.slice(0, MAX_STORE_SLUG_LENGTH).replace(/-+$/g, "")
      : ascii;

  console.assert(truncated.length > 0, "buildStoreSlug: result must not be empty");
  console.assert(truncated.length <= MAX_STORE_SLUG_LENGTH, "buildStoreSlug: result exceeds MAX_STORE_SLUG_LENGTH");
  console.assert(!truncated.includes("--"), "buildStoreSlug: result must not contain double hyphens");

  return truncated;
}

/**
 * Returns the canonical site-relative path for a store, given its slug.
 * Centralised so that callers (links, sitemap, JSON-LD, canonical tag)
 * cannot drift apart.
 */
/**
 * Returns the best site-relative path for a store. Prefers the
 * human-readable slug; falls back to the legacy ``/store/<uuid>`` form
 * for rows that have not yet been backfilled. The legacy form is still
 * served (via 301 redirect) by the ``[slug]`` route.
 */
export function storeHref(store: { id: string; slug: string | null }): string {
  console.assert(typeof store === "object" && store !== null, "storeHref: store must be an object");
  console.assert(typeof store.id === "string" && store.id.length > 0, "storeHref: store.id must be non-empty");
  if (store.slug !== null && store.slug.length > 0) {
    return storeSlugPath(store.slug);
  }
  return `/store/${store.id}`;
}

export function storeSlugPath(slug: string): string {
  console.assert(typeof slug === "string" && slug.length > 0, "storeSlugPath: slug must be non-empty");
  console.assert(slug.length <= MAX_STORE_SLUG_LENGTH, "storeSlugPath: slug too long");
  return `/store/${slug}`;
}


/**
 * Maps lowercase state names to two-letter abbreviations (all 50 states + DC).
 */
export const STATE_ABBREVIATIONS: Record<string, string> = {
  alabama: "AL",
  alaska: "AK",
  arizona: "AZ",
  arkansas: "AR",
  california: "CA",
  colorado: "CO",
  connecticut: "CT",
  delaware: "DE",
  "district of columbia": "DC",
  florida: "FL",
  georgia: "GA",
  hawaii: "HI",
  idaho: "ID",
  illinois: "IL",
  indiana: "IN",
  iowa: "IA",
  kansas: "KS",
  kentucky: "KY",
  louisiana: "LA",
  maine: "ME",
  maryland: "MD",
  massachusetts: "MA",
  michigan: "MI",
  minnesota: "MN",
  mississippi: "MS",
  missouri: "MO",
  montana: "MT",
  nebraska: "NE",
  nevada: "NV",
  "new hampshire": "NH",
  "new jersey": "NJ",
  "new mexico": "NM",
  "new york": "NY",
  "north carolina": "NC",
  "north dakota": "ND",
  ohio: "OH",
  oklahoma: "OK",
  oregon: "OR",
  pennsylvania: "PA",
  "rhode island": "RI",
  "south carolina": "SC",
  "south dakota": "SD",
  tennessee: "TN",
  texas: "TX",
  utah: "UT",
  vermont: "VT",
  virginia: "VA",
  washington: "WA",
  "west virginia": "WV",
  wisconsin: "WI",
  wyoming: "WY",
};

/**
 * Maps URL slugs back to proper-cased state names.
 * Built automatically from STATE_ABBREVIATIONS.
 */
export const SLUG_TO_STATE: Record<string, string> = (() => {
  const result: Record<string, string> = {};
  const keys = Object.keys(STATE_ABBREVIATIONS);
  for (let i = 0; i < keys.length && i < 60; i++) {
    const name = keys[i];
    const slug = name.replace(/ /g, "-");
    result[slug] = name
      .split(" ")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }
  return result;
})();

/**
 * Maps two-letter uppercase abbreviations back to URL slugs.
 * Example: "TX" → "texas", "NY" → "new-york"
 */
export const ABBREV_TO_SLUG: Record<string, string> = (() => {
  const result: Record<string, string> = {};
  const keys = Object.keys(STATE_ABBREVIATIONS);
  for (let i = 0; i < keys.length && i < 60; i++) {
    const name = keys[i];
    const abbr = STATE_ABBREVIATIONS[name];
    result[abbr] = name.replace(/ /g, "-");
  }
  return result;
})();

/**
 * Maps two-letter uppercase abbreviations to proper-cased state names.
 * Example: "TX" → "Texas", "NY" → "New York"
 */
export const ABBREV_TO_STATE_NAME: Record<string, string> = (() => {
  const result: Record<string, string> = {};
  const keys = Object.keys(STATE_ABBREVIATIONS);
  for (let i = 0; i < keys.length && i < 60; i++) {
    const name = keys[i];
    const abbr = STATE_ABBREVIATIONS[name];
    result[abbr] = name
      .split(" ")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }
  return result;
})();

/**
 * Converts a state name OR abbreviation to a URL slug.
 * Example: "New York" → "new-york", "NY" → "new-york", "TX" → "texas"
 */
export function stateToSlug(state: string): string {
  console.assert(typeof state === "string", "stateToSlug: state must be a string");
  console.assert(state.length > 0, "stateToSlug: state must not be empty");

  const trimmed = state.trim();
  const upper = trimmed.toUpperCase();

  // Check if input is a 2-letter abbreviation
  if (trimmed.length === 2 && ABBREV_TO_SLUG[upper] !== undefined) {
    const slug = ABBREV_TO_SLUG[upper];
    console.assert(slug.length <= MAX_SLUG_LENGTH, "stateToSlug: slug exceeds MAX_SLUG_LENGTH");
    console.assert(slug.length > 0, "stateToSlug: slug must not be empty");
    return slug;
  }

  const slug = trimmed.toLowerCase().replace(/ /g, "-");

  console.assert(slug.length <= MAX_SLUG_LENGTH, "stateToSlug: slug exceeds MAX_SLUG_LENGTH");
  console.assert(!slug.includes("  "), "stateToSlug: slug must not contain double spaces");

  return slug;
}

/**
 * Converts a city name to a URL slug.
 * Strips non-alphanumeric characters (except spaces and hyphens),
 * then collapses multiple hyphens.
 * Example: "San Francisco" → "san-francisco"
 */
export function cityToSlug(city: string): string {
  console.assert(typeof city === "string", "cityToSlug: city must be a string");
  console.assert(city.length > 0, "cityToSlug: city must not be empty");

  const stripped = city.trim().replace(/[^a-zA-Z0-9 -]/g, "");
  const slug = stripped
    .toLowerCase()
    .replace(/ /g, "-")
    .replace(/-{2,}/g, "-")
    .replace(/^-|-$/g, "");

  console.assert(slug.length <= MAX_SLUG_LENGTH, "cityToSlug: slug exceeds MAX_SLUG_LENGTH");
  console.assert(!slug.includes("--"), "cityToSlug: slug must not contain consecutive hyphens");

  return slug;
}

/**
 * Converts a URL slug back to a proper-cased state name using the known states map.
 * Returns null if the slug does not match a known state.
 * Example: "new-york" → "New York"
 */
export function slugToState(slug: string): string | null {
  console.assert(typeof slug === "string", "slugToState: slug must be a string");
  console.assert(slug.length > 0, "slugToState: slug must not be empty");

  const result = SLUG_TO_STATE[slug] ?? null;

  console.assert(result === null || result.length > 0, "slugToState: result must be non-empty when found");
  console.assert(result === null || typeof result === "string", "slugToState: result must be a string or null");

  return result;
}

/**
 * Converts a URL slug to a two-letter state abbreviation using the known states map.
 * Returns null if the slug does not match a known state.
 * Example: "new-york" → "NY"
 */
export function slugToAbbreviation(slug: string): string | null {
  console.assert(typeof slug === "string", "slugToAbbreviation: slug must be a string");
  console.assert(slug.length > 0, "slugToAbbreviation: slug must not be empty");

  const stateName = SLUG_TO_STATE[slug];
  if (stateName === undefined) {
    return null;
  }

  const abbr = STATE_ABBREVIATIONS[stateName.toLowerCase()] ?? null;

  console.assert(abbr === null || abbr.length === 2, "slugToAbbreviation: abbreviation must be 2 characters");
  console.assert(abbr === null || abbr === abbr.toUpperCase(), "slugToAbbreviation: abbreviation must be uppercase");

  return abbr;
}

/**
 * Converts a two-letter state abbreviation to a proper-cased state name.
 * Returns null if the abbreviation is not recognized.
 * Example: "TX" → "Texas", "NY" → "New York"
 */
export function abbreviationToStateName(abbr: string): string | null {
  console.assert(typeof abbr === "string", "abbreviationToStateName: abbr must be a string");
  console.assert(abbr.length > 0, "abbreviationToStateName: abbr must not be empty");

  const result = ABBREV_TO_STATE_NAME[abbr.toUpperCase()] ?? null;

  console.assert(result === null || result.length > 0, "abbreviationToStateName: result must be non-empty when found");
  console.assert(result === null || typeof result === "string", "abbreviationToStateName: result must be a string or null");

  return result;
}

/**
 * Converts a URL slug to a title-cased city name (generic, no lookup).
 * Example: "san-francisco" → "San Francisco"
 */
export function slugToCity(slug: string): string {
  console.assert(typeof slug === "string", "slugToCity: slug must be a string");
  console.assert(slug.length > 0, "slugToCity: slug must not be empty");

  const city = slug
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");

  console.assert(city.length > 0, "slugToCity: result must not be empty");
  console.assert(!city.includes("-"), "slugToCity: result must not contain hyphens");

  return city;
}
