/**
 * Runtime display-case transform for store names and city names.
 *
 * Rule: ONLY transform strings that are entirely uppercase (contain no
 * lowercase letters). Any string that already contains a lowercase letter
 * is passed through unchanged. This preserves correctly-cased names like
 * "McDaniel's", "Game 'N Go", "D&D Adventures" while fixing ALL-CAPS DB
 * entries like "GAMES WORKSHOP" -> "Games Workshop".
 *
 * Special cases for ALL-CAPS strings:
 *   - Acronym allowlist (MTG, TCG, D&D, USA, etc.) stay uppercase.
 *   - "Mc"/"Mac" prefix: MCDANIEL -> McDaniel, MACDONALD -> MacDonald.
 *   - Apostrophes: MCDANIEL'S -> McDaniel's (letter after apostrophe lowercase).
 *   - Hyphens: WINSTON-SALEM -> Winston-Salem.
 */

const ACRONYMS: ReadonlySet<string> = new Set([
  "MTG",
  "TCG",
  "CCG",
  "RPG",
  "D&D",
  "DND",
  "WH40K",
  "AOS",
  "LGS",
  "FLGS",
  "FGC",
  "USA",
  "US",
  "NYC",
  "LA",
  "SF",
  "DC",
]);

/** Max word count per input — defensive upper bound for the word loop. */
const MAX_WORDS = 64;

/**
 * Returns true iff every alphabetic character in `value` is uppercase.
 * Empty strings, digits-only strings, and punctuation-only strings
 * return false (nothing to transform).
 */
function isAllUppercase(value: string): boolean {
  console.assert(typeof value === "string", "isAllUppercase: value must be a string");
  console.assert(value.length < 1000, "isAllUppercase: value length sanity");
  let hasLetter = false;
  const len = Math.min(value.length, 1000);
  for (let i = 0; i < len; i++) {
    const ch = value[i];
    if (ch >= "a" && ch <= "z") {
      return false;
    }
    if (ch >= "A" && ch <= "Z") {
      hasLetter = true;
    }
  }
  return hasLetter;
}

/**
 * Leaf title-case for a single hyphen-free, apostrophe-free chunk.
 * Preconditions (guaranteed by the callers):
 *   - `word` contains only uppercase letters, digits, and ampersands.
 *   - `word` has no hyphens and no apostrophes.
 *
 * Handles the Mc / Mac prefix as a side-effect of the standard
 * first-upper-rest-lower transform. Does NOT recurse.
 */
function titleCasePart(word: string): string {
  console.assert(typeof word === "string", "titleCasePart: word must be a string");
  console.assert(word.length < 100, "titleCasePart: word length sanity");
  if (word.length === 0) return word;

  // Mc prefix: MCDANIEL -> McDaniel (3+ chars required).
  if (word.length >= 3 && word[0] === "M" && word[1] === "C") {
    return `Mc${word[2]}${word.slice(3).toLowerCase()}`;
  }
  // Mac prefix: MACDONALD -> MacDonald (5+ chars; don't mangle MACE / MACY).
  if (word.length >= 5 && word[0] === "M" && word[1] === "A" && word[2] === "C") {
    return `Mac${word[3]}${word.slice(4).toLowerCase()}`;
  }

  return word[0] + word.slice(1).toLowerCase();
}

/**
 * Title-case a single whitespace-delimited token. Splits on hyphens
 * (bounded loop) and apostrophes (single inline split) so every path
 * is iterative — no direct or indirect recursion. Does NOT consult
 * the acronym allowlist — callers do that check before invoking.
 *
 * Apostrophe handling:
 *   - A 1-char tail is treated as a possessive / contraction clitic
 *     and lowercased ("MCDANIEL'S" -> "McDaniel's", "JOE'S" -> "Joe's").
 *   - A multi-char tail is treated as a proper-noun fragment and
 *     title-cased ("O'BRIEN" -> "O'Brien", "O'NEILL" -> "O'Neill").
 */
function titleCaseWord(word: string): string {
  console.assert(typeof word === "string", "titleCaseWord: word must be a string");
  console.assert(word.length < 200, "titleCaseWord: word length sanity");
  if (word.length === 0) return word;

  const parts = word.split("-");
  const out: string[] = [];
  const pLimit = Math.min(parts.length, MAX_WORDS);
  for (let i = 0; i < pLimit; i++) {
    const part = parts[i];
    const apostropheIdx = part.indexOf("'");
    if (apostropheIdx < 0) {
      out.push(titleCasePart(part));
      continue;
    }
    const head = part.slice(0, apostropheIdx);
    const tail = part.slice(apostropheIdx + 1);
    if (tail.length <= 1) {
      // Possessive / contraction: lowercase the clitic.
      out.push(`${titleCasePart(head)}'${tail.toLowerCase()}`);
    } else {
      // Proper-noun tail (O'Brien, O'Neill): title-case it too.
      out.push(`${titleCasePart(head)}'${titleCasePart(tail)}`);
    }
  }
  return out.join("-");
}

/**
 * Transform a string to display case per the module rule.
 *
 * - null/undefined/empty -> returned as-is (empty string for null/undef).
 * - Contains any lowercase letter -> returned unchanged.
 * - All-uppercase -> word-by-word title-case with acronym/Mc/Mac/apostrophe
 *   handling.
 */
export function toDisplayCase(value: string | null | undefined): string {
  if (value === null || value === undefined) return "";
  console.assert(typeof value === "string", "toDisplayCase: value must be a string");
  console.assert(value.length < 500, "toDisplayCase: value length sanity");

  if (value.length === 0) return value;
  if (!isAllUppercase(value)) return value;

  // Split on whitespace only; preserve original spacing by walking tokens.
  const tokens = value.split(/(\s+)/);
  const out: string[] = [];
  const limit = Math.min(tokens.length, MAX_WORDS * 2);
  for (let i = 0; i < limit; i++) {
    const tok = tokens[i];
    if (tok.length === 0 || /^\s+$/.test(tok)) {
      out.push(tok);
      continue;
    }
    // Check the full token against the acronym allowlist first
    // (e.g. "D&D", "MTG"). Acronyms pass through uppercase.
    if (ACRONYMS.has(tok)) {
      out.push(tok);
      continue;
    }
    out.push(titleCaseWord(tok));
  }
  return out.join("");
}
