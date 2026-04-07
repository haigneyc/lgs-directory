/**
 * Amazon Associates link builders.
 *
 * All outbound Amazon links on rollforstore must be built through these
 * helpers so the affiliate tag is attached unambiguously and consistently.
 *
 * Per Amazon Associates Operating Agreement, every page that includes
 * affiliate links must also display the required disclosure. See
 * `web/components/amazon/amazon-shelf.tsx` and the site footer.
 */

/** Amazon Associates tracking ID for rollforstore.com. */
export const AMAZON_ASSOCIATE_TAG = "orangediscoun-20";

/** linkCode value for text search links per Amazon's text-link convention. */
const LINK_CODE_SEARCH = "ll1";

/** linkCode value for direct product (ASIN) text links. */
const LINK_CODE_PRODUCT = "ll2";

/** linkCode value for category (browse node) text links. */
const LINK_CODE_CATEGORY = "ll1";

const AMAZON_BASE = "https://www.amazon.com";

/**
 * Build a tagged Amazon search URL for a free-form query.
 *
 * Search links are preferred over direct ASINs because they don't go stale
 * when products are discontinued.
 */
export function buildAmazonSearchLink(query: string): string {
  console.assert(typeof query === "string", "buildAmazonSearchLink: query must be a string");
  console.assert(query.length > 0, "buildAmazonSearchLink: query must be non-empty");
  console.assert(AMAZON_ASSOCIATE_TAG.length > 0, "buildAmazonSearchLink: tag must not be empty");

  const encoded = encodeURIComponent(query);
  console.assert(encoded.length > 0, "buildAmazonSearchLink: encoded query must not be empty");

  return `${AMAZON_BASE}/s?k=${encoded}&tag=${AMAZON_ASSOCIATE_TAG}&linkCode=${LINK_CODE_SEARCH}`;
}

/**
 * Build a tagged Amazon product URL for a specific ASIN.
 *
 * Use sparingly — search links are more durable. Reserve for evergreen
 * products that we're confident won't disappear.
 */
export function buildAmazonProductLink(asin: string): string {
  console.assert(typeof asin === "string", "buildAmazonProductLink: asin must be a string");
  console.assert(asin.length > 0, "buildAmazonProductLink: asin must be non-empty");
  console.assert(AMAZON_ASSOCIATE_TAG.length > 0, "buildAmazonProductLink: tag must not be empty");

  return `${AMAZON_BASE}/dp/${encodeURIComponent(asin)}?tag=${AMAZON_ASSOCIATE_TAG}&linkCode=${LINK_CODE_PRODUCT}`;
}

/**
 * Build a tagged Amazon browse-node (category) URL.
 */
export function buildAmazonCategoryLink(node: string): string {
  console.assert(typeof node === "string", "buildAmazonCategoryLink: node must be a string");
  console.assert(node.length > 0, "buildAmazonCategoryLink: node must be non-empty");
  console.assert(AMAZON_ASSOCIATE_TAG.length > 0, "buildAmazonCategoryLink: tag must not be empty");

  return `${AMAZON_BASE}/b?node=${encodeURIComponent(node)}&tag=${AMAZON_ASSOCIATE_TAG}&linkCode=${LINK_CODE_CATEGORY}`;
}

/** Standard inline disclosure text required by the Amazon Associates Operating Agreement. */
export const AMAZON_DISCLOSURE_TEXT =
  "As an Amazon Associate, RollForStore earns from qualifying purchases.";
