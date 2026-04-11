"use client";

import { useActionState } from "react";
import { submitClaim, type ClaimFormState } from "@/lib/claim-actions";
import { CLAIM_ROLES } from "@/lib/types";

const INITIAL_STATE: ClaimFormState = { success: false, error: null };
const CLAIM_ROLES_LENGTH = 4;

const ROLE_LABELS: Record<string, string> = {
  owner: "Owner",
  manager: "Manager",
  employee: "Employee",
  other: "Other",
};

const INPUT_CLASS =
  "w-full rounded-lg border border-zinc-700 bg-zinc-800/50 px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:border-yellow-500/50 focus:outline-none focus:ring-1 focus:ring-yellow-500/30 transition-colors";

interface ClaimFormProps {
  storeId: string;
  storeName: string;
}

function ClaimSuccess({ storeName }: { storeName: string }) {
  console.assert(typeof storeName === "string", "ClaimSuccess: storeName must be a string");
  console.assert(storeName.length > 0, "ClaimSuccess: storeName must be non-empty");

  return (
    <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-8 text-center">
      <h2 className="font-display text-2xl font-bold text-emerald-400 mb-3">
        Claim Submitted
      </h2>
      <p className="text-zinc-300 max-w-md mx-auto">
        Thanks for claiming <span className="font-semibold">{storeName}</span>.
        We&apos;ll review your claim within 24-48 hours and email you at the
        address you provided.
      </p>
    </div>
  );
}

function RoleSelect() {
  console.assert(CLAIM_ROLES.length === CLAIM_ROLES_LENGTH, "RoleSelect: CLAIM_ROLES length mismatch");
  console.assert(typeof ROLE_LABELS === "object", "RoleSelect: ROLE_LABELS must be an object");

  return (
    <div>
      <label htmlFor="claim-role" className="block text-sm font-medium text-zinc-300 mb-1.5">
        Your Role
      </label>
      <select
        id="claim-role"
        name="role"
        required
        className={INPUT_CLASS}
        defaultValue=""
      >
        <option value="" disabled>
          Select your role
        </option>
        {CLAIM_ROLES.map((role) => (
          <option key={role} value={role}>
            {ROLE_LABELS[role] ?? role}
          </option>
        ))}
      </select>
    </div>
  );
}

export function ClaimForm({ storeId, storeName }: ClaimFormProps) {
  console.assert(typeof storeId === "string" && storeId.length > 0, "ClaimForm: storeId must be non-empty");
  console.assert(typeof storeName === "string" && storeName.length > 0, "ClaimForm: storeName must be non-empty");

  const [state, formAction, isPending] = useActionState(submitClaim, INITIAL_STATE);

  if (state.success) {
    return <ClaimSuccess storeName={storeName} />;
  }

  return (
    <form action={formAction} className="space-y-6">
      <input type="hidden" name="storeId" value={storeId} />

      {state.error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {state.error}
        </div>
      )}

      <div>
        <label htmlFor="claim-name" className="block text-sm font-medium text-zinc-300 mb-1.5">
          Your Name
        </label>
        <input id="claim-name" name="name" type="text" required maxLength={200} className={INPUT_CLASS} placeholder="John Smith" />
      </div>

      <div>
        <label htmlFor="claim-email" className="block text-sm font-medium text-zinc-300 mb-1.5">
          Email Address
        </label>
        <input id="claim-email" name="email" type="email" required maxLength={254} className={INPUT_CLASS} placeholder="you@yourstore.com" />
      </div>

      <RoleSelect />

      <div>
        <label htmlFor="claim-proof" className="block text-sm font-medium text-zinc-300 mb-1.5">
          Proof of Ownership
        </label>
        <textarea
          id="claim-proof"
          name="proofText"
          required
          minLength={10}
          maxLength={2000}
          rows={4}
          className={`${INPUT_CLASS} resize-y`}
          placeholder="e.g., I'm the owner — here's our Facebook page: facebook.com/mystore"
        />
        <p className="mt-1 text-xs text-zinc-500">
          Provide a brief explanation of your connection to this store (10+ characters).
        </p>
      </div>

      <button
        type="submit"
        disabled={isPending}
        className="w-full rounded-lg bg-yellow-600 px-6 py-3 text-sm font-semibold text-zinc-950 hover:bg-yellow-500 focus:outline-none focus:ring-2 focus:ring-yellow-500/50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isPending ? "Submitting..." : "Submit Claim"}
      </button>
    </form>
  );
}
