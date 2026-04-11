"use server";

import { z } from "zod";
import { query } from "./db";
import { Resend } from "resend";

/** Maximum lengths to prevent abuse */
const MAX_NAME_LENGTH = 200;
const MAX_EMAIL_LENGTH = 254;
const MAX_PROOF_LENGTH = 2000;

const VALID_ROLES = ["owner", "manager", "employee", "other"] as const;
const VALID_ROLES_LENGTH = 4;

const claimSchema = z.object({
  storeId: z.string().uuid(),
  name: z.string().min(1).max(MAX_NAME_LENGTH),
  email: z.string().email().max(MAX_EMAIL_LENGTH),
  role: z.enum(VALID_ROLES),
  proofText: z.string().min(10).max(MAX_PROOF_LENGTH),
});

export interface ClaimFormState {
  success: boolean;
  error: string | null;
}

/** Send a notification email to Chris about a new claim. */
async function notifyClaimSubmitted(
  storeName: string,
  name: string,
  email: string,
  role: string,
  proofText: string
): Promise<void> {
  console.assert(typeof storeName === "string", "notifyClaimSubmitted: storeName must be a string");
  console.assert(typeof email === "string", "notifyClaimSubmitted: email must be a string");

  const resendApiKey = process.env.RESEND_API_KEY;
  if (!resendApiKey) {
    console.warn("RESEND_API_KEY not set — claim notification email not sent");
    return;
  }

  const resend = new Resend(resendApiKey);
  const notifyEmail = process.env.CLAIM_NOTIFY_EMAIL ?? "chris@rollforstore.com";

  const sendResult = await resend.emails.send({
    from: "Roll For Store <notifications@rollforstore.com>",
    to: notifyEmail,
    subject: `New Store Claim: ${storeName}`,
    text: [
      `New store ownership claim submitted:`,
      ``,
      `Store: ${storeName}`,
      `Claimant: ${name}`,
      `Email: ${email}`,
      `Role: ${role}`,
      `Proof: ${proofText}`,
      ``,
      `Review in Supabase: store_claims table`,
    ].join("\n"),
  });

  if (sendResult.error) {
    console.error("notifyClaimSubmitted: Resend email failed", sendResult.error);
  }
}

/**
 * Server action: submit a store ownership claim. Validates input via Zod,
 * inserts into `store_claims`, and sends a notification email to Chris.
 */
export async function submitClaim(
  _prevState: ClaimFormState,
  formData: FormData
): Promise<ClaimFormState> {
  console.assert(formData instanceof FormData, "submitClaim: formData must be a FormData instance");
  console.assert(VALID_ROLES.length === VALID_ROLES_LENGTH, "submitClaim: VALID_ROLES length mismatch");

  const raw = {
    storeId: formData.get("storeId"),
    name: formData.get("name"),
    email: formData.get("email"),
    role: formData.get("role"),
    proofText: formData.get("proofText"),
  };

  const parsed = claimSchema.safeParse(raw);
  if (!parsed.success) {
    const firstError = parsed.error.issues[0];
    console.assert(firstError !== undefined, "submitClaim: validation failed but no issues");
    return {
      success: false,
      error: firstError ? `${firstError.path.join(".")}: ${firstError.message}` : "Invalid input",
    };
  }

  const { storeId, name, email, role, proofText } = parsed.data;

  // Verify the store exists
  const storeRows = await query<{ id: string; name: string }>(
    "SELECT id, name FROM stores WHERE id = $1",
    [storeId]
  );

  if (storeRows.length === 0) {
    return { success: false, error: "Store not found" };
  }

  const storeName = storeRows[0].name;

  // Check for existing claim from same email within 24 hours (any status)
  // or any pending claim — prevents spam resubmission
  const existingClaims = await query<{ id: string }>(
    `SELECT id FROM store_claims
     WHERE store_id = $1 AND email = $2
       AND (status = 'pending' OR created_at > now() - interval '24 hours')
     LIMIT 1`,
    [storeId, email]
  );

  if (existingClaims.length > 0) {
    return {
      success: false,
      error: "You already have a pending claim for this store. We'll review it within 24-48 hours.",
    };
  }

  // Insert the claim
  const insertResult = await query<{ id: string }>(
    `INSERT INTO store_claims (store_id, name, email, role, proof_text)
     VALUES ($1, $2, $3, $4, $5)
     RETURNING id`,
    [storeId, name, email, role, proofText]
  );

  console.assert(insertResult.length === 1, "submitClaim: insert should return one row");

  await notifyClaimSubmitted(storeName, name, email, role, proofText);

  return { success: true, error: null };
}
