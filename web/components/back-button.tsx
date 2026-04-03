"use client";

import { useRouter } from "next/navigation";

/**
 * Client component that navigates back via browser history,
 * preserving any filter/search state the user had on the browse page.
 * Falls back to "/" if there is no history entry.
 */
export function BackButton() {
  const router = useRouter();

  function handleClick() {
    // window.history.length > 1 indicates a previous page exists
    const hasPreviousPage = typeof window !== "undefined" && window.history.length > 1;

    if (hasPreviousPage) {
      router.back();
    } else {
      router.push("/");
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors mb-4 inline-block"
    >
      &larr; Back to browse
    </button>
  );
}
