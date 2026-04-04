import type { StoreWithPresences, StoreEnrichment, StoreContent } from "./types";
import { formatProduct, formatAddress } from "./format";

export interface FaqItem {
  question: string;
  answer: string;
}

interface GenerateFaqParams {
  store: StoreWithPresences;
  enrichment: StoreEnrichment | null;
  storeContent: StoreContent | null;
}

const MAX_FAQ_ITEMS = 12;
const MAX_PRODUCTS_IN_ANSWER = 8;

/**
 * Generates FAQ items from store data. Only includes questions where we have
 * data to provide a meaningful answer.
 */
export function generateStoreFaq(params: GenerateFaqParams): FaqItem[] {
  console.assert(params.store !== null, "generateStoreFaq: store must not be null");
  console.assert(typeof params.store.name === "string", "generateStoreFaq: store.name must be a string");

  const { store, enrichment, storeContent } = params;
  const items: FaqItem[] = [];

  // Location question -- always available (stores always have addresses)
  items.push({
    question: `Where is ${store.name} located?`,
    answer: `${store.name} is located at ${formatAddress(store.address)}.`,
  });

  // Phone number
  if (store.phone) {
    items.push({
      question: `What is ${store.name}'s phone number?`,
      answer: `You can reach ${store.name} by phone at ${store.phone}.`,
    });
  }

  // Business hours
  if (enrichment?.hours_weekday_text !== null && enrichment?.hours_weekday_text !== undefined && enrichment.hours_weekday_text.length > 0) {
    const hoursText = enrichment.hours_weekday_text.join(", ");
    items.push({
      question: `What are ${store.name}'s hours?`,
      answer: `${store.name}'s hours are: ${hoursText}.`,
    });
  }

  // Website
  const websitePresence = store.presences.find(
    (p) => p.channel_type === "website" && p.status === "active"
  );
  if (websitePresence) {
    items.push({
      question: `Does ${store.name} have a website?`,
      answer: `Yes, you can visit ${store.name}'s website at ${websitePresence.url}.`,
    });
  }

  // Games & products overview
  if (storeContent !== null && storeContent.products.length > 0) {
    const cappedProducts = storeContent.products.slice(0, MAX_PRODUCTS_IN_ANSWER);
    const productNames = cappedProducts.map(formatProduct);
    items.push({
      question: `What games does ${store.name} sell?`,
      answer: `${store.name} carries ${productNames.join(", ")}.`,
    });
  }

  // Specific game queries -- only add when the store carries the product
  if (storeContent !== null && storeContent.products.includes("mtg")) {
    items.push({
      question: `Does ${store.name} sell Magic: The Gathering cards?`,
      answer: `Yes, ${store.name} sells Magic: The Gathering cards.`,
    });
  }

  if (storeContent !== null && storeContent.products.includes("pokemon")) {
    items.push({
      question: `Does ${store.name} sell Pokemon cards?`,
      answer: `Yes, ${store.name} sells Pokemon TCG cards.`,
    });
  }

  if (storeContent !== null && storeContent.products.includes("miniatures")) {
    items.push({
      question: `Does ${store.name} have Warhammer products?`,
      answer: `Yes, ${store.name} carries Warhammer and miniatures products.`,
    });
  }

  // Events
  if (storeContent?.has_events) {
    const eventDetail = storeContent.event_url
      ? ` Check their events schedule at ${storeContent.event_url}.`
      : "";
    items.push({
      question: `Does ${store.name} host events?`,
      answer: `Yes, ${store.name} hosts in-store events.${eventDetail}`,
    });
  }

  // MTG singles online
  const sellsSingles = store.presences.some((p) => p.sells_mtg_singles === true);
  if (sellsSingles) {
    items.push({
      question: `Can I buy Magic: The Gathering singles from ${store.name} online?`,
      answer: `Yes, ${store.name} sells Magic: The Gathering singles through their online presence.`,
    });
  }

  // WPN status
  if (store.wpn_level) {
    const levelLabel = store.wpn_level === "premium" ? "WPN Premium" : "WPN Core";
    items.push({
      question: `Is ${store.name} a WPN store?`,
      answer: `Yes, ${store.name} is a ${levelLabel} member of Wizards Play Network.`,
    });
  }

  // Google rating
  if (enrichment?.rating !== null && enrichment?.rating !== undefined && enrichment?.user_rating_count !== null && enrichment?.user_rating_count !== undefined) {
    items.push({
      question: `What is ${store.name}'s rating?`,
      answer: `${store.name} has a ${enrichment.rating.toFixed(1)} out of 5 star rating on Google based on ${enrichment.user_rating_count} reviews.`,
    });
  }

  console.assert(Array.isArray(items), "generateStoreFaq: items must be an array");

  const result = items.slice(0, MAX_FAQ_ITEMS);
  console.assert(result.length <= MAX_FAQ_ITEMS, "generateStoreFaq: result must not exceed MAX_FAQ_ITEMS");

  return result;
}

/**
 * Builds FAQPage JSON-LD structured data from FAQ items.
 */
export function buildFaqJsonLd(items: FaqItem[]): Record<string, unknown> {
  console.assert(Array.isArray(items), "buildFaqJsonLd: items must be an array");
  console.assert(items.length > 0, "buildFaqJsonLd: items must not be empty");

  const maxItems = Math.min(items.length, MAX_FAQ_ITEMS);
  const mainEntity: Record<string, unknown>[] = [];

  for (let i = 0; i < maxItems; i++) {
    const item = items[i];
    console.assert(typeof item.question === "string", "buildFaqJsonLd: question must be a string");
    console.assert(typeof item.answer === "string", "buildFaqJsonLd: answer must be a string");

    mainEntity.push({
      "@type": "Question",
      name: item.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.answer,
      },
    });
  }

  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity,
  };
}
