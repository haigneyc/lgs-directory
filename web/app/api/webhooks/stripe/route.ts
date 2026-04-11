import { NextRequest } from "next/server";
import Stripe from "stripe";
import { query } from "@/lib/db";

/**
 * Stripe webhook handler for premium store subscriptions.
 *
 * Handles:
 * - customer.subscription.created  -> premium_status = 'premium'
 * - customer.subscription.deleted  -> premium_status = 'claimed'
 * - invoice.payment_failed         -> log for manual follow-up
 *
 * The store is identified via the subscription's metadata.store_id field,
 * which Chris sets when creating the Stripe Payment Link / subscription.
 */

/** Activate a premium subscription for a store. */
async function handleSubscriptionCreated(
  subscription: Stripe.Subscription
): Promise<void> {
  const storeId = subscription.metadata?.store_id;
  console.assert(typeof subscription.id === "string", "handleSubscriptionCreated: subscription.id must be a string");

  if (!storeId) {
    console.error("stripe webhook: subscription.created missing store_id in metadata");
    return;
  }

  // Stripe API versions >=2024 moved current_period_end from the
  // subscription object to subscription items. Check both locations so
  // the webhook works regardless of API version.
  const subRecord = subscription as unknown as Record<string, unknown>;
  const periodEnd =
    typeof subRecord.current_period_end === "number"
      ? subRecord.current_period_end
      : subscription.items.data[0]?.current_period_end;
  console.assert(
    typeof periodEnd === "number" || periodEnd === undefined,
    "handleSubscriptionCreated: periodEnd must be a number or undefined"
  );

  const premiumUntil = periodEnd
    ? new Date(periodEnd * 1000).toISOString()
    : null;

  const rows = await query(
    `UPDATE stores
     SET premium_status = 'premium',
         premium_until = $1
     WHERE id = $2
     RETURNING id`,
    [premiumUntil, storeId]
  );

  if (rows.length === 0) {
    console.error("stripe webhook: store not found for subscription.created", storeId);
  }
}

/** Deactivate a premium subscription (downgrade to claimed). */
async function handleSubscriptionDeleted(
  subscription: Stripe.Subscription
): Promise<void> {
  const storeId = subscription.metadata?.store_id;
  console.assert(typeof subscription.id === "string", "handleSubscriptionDeleted: subscription.id must be a string");

  if (!storeId) {
    console.error("stripe webhook: subscription.deleted missing store_id in metadata");
    return;
  }

  console.assert(typeof storeId === "string", "handleSubscriptionDeleted: storeId must be a string");

  const rows = await query(
    `UPDATE stores
     SET premium_status = 'claimed',
         premium_until = NULL
     WHERE id = $1
     RETURNING id`,
    [storeId]
  );

  if (rows.length === 0) {
    console.error("stripe webhook: store not found for subscription.deleted", storeId);
  }
}

/** Log a failed payment for manual follow-up. */
function handlePaymentFailed(invoice: Stripe.Invoice): void {
  console.assert(typeof invoice.id === "string", "handlePaymentFailed: invoice.id must be a string");
  const customerEmail = typeof invoice.customer_email === "string"
    ? invoice.customer_email
    : "unknown";
  console.assert(typeof customerEmail === "string", "handlePaymentFailed: customerEmail must be a string");
  console.error(
    "stripe webhook: invoice.payment_failed for customer",
    customerEmail
  );
}

/** Verify the Stripe webhook signature and return the parsed event. */
function verifyWebhookSignature(
  stripe: Stripe,
  body: string,
  signature: string,
  secret: string
): Stripe.Event | null {
  console.assert(typeof body === "string", "verifyWebhookSignature: body must be a string");
  console.assert(typeof signature === "string", "verifyWebhookSignature: signature must be a string");

  try {
    return stripe.webhooks.constructEvent(body, signature, secret);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("stripe webhook: signature verification failed", message);
    return null;
  }
}

export async function POST(request: NextRequest) {
  console.assert(request instanceof Request, "POST: request must be a Request");
  console.assert(typeof request.headers.get === "function", "POST: request.headers must have get()");

  const stripeSecretKey = process.env.STRIPE_SECRET_KEY;
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

  if (!stripeSecretKey || !webhookSecret) {
    console.error("stripe webhook: missing STRIPE_SECRET_KEY or STRIPE_WEBHOOK_SECRET");
    return Response.json({ error: "Webhook not configured" }, { status: 500 });
  }

  const stripe = new Stripe(stripeSecretKey);
  const body = await request.text();
  const signature = request.headers.get("stripe-signature");

  if (!signature) {
    return Response.json({ error: "Missing stripe-signature header" }, { status: 400 });
  }

  const event = verifyWebhookSignature(stripe, body, signature, webhookSecret);
  if (!event) {
    return Response.json({ error: "Invalid signature" }, { status: 400 });
  }

  if (event.type === "customer.subscription.created") {
    await handleSubscriptionCreated(event.data.object as Stripe.Subscription);
  }

  if (event.type === "customer.subscription.deleted") {
    await handleSubscriptionDeleted(event.data.object as Stripe.Subscription);
  }

  if (event.type === "invoice.payment_failed") {
    handlePaymentFailed(event.data.object as Stripe.Invoice);
  }

  return Response.json({ received: true });
}
