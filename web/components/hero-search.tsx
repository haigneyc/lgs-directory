"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, MapPin } from "lucide-react";

/**
 * Prominent search bar for the homepage hero section.
 * Supports text search and geolocation shortcut.
 */
export function HeroSearch() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  console.assert(typeof query === "string", "HeroSearch: query must be a string");

  const MAX_QUERY_LENGTH = 200;

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const trimmed = query.trim();

      console.assert(typeof trimmed === "string", "HeroSearch.handleSubmit: trimmed must be a string");
      console.assert(trimmed.length <= MAX_QUERY_LENGTH, "HeroSearch.handleSubmit: query too long");

      if (trimmed.length === 0) {
        return;
      }
      router.push(`/?q=${encodeURIComponent(trimmed)}`);
    },
    [query, router]
  );

  const handleNearMe = useCallback(() => {
    router.push("/near-me");
  }, [router]);

  return (
    <div className="max-w-xl mx-auto">
      <form onSubmit={handleSubmit} className="relative">
        <div className="flex items-center rounded-xl border border-zinc-700/60 bg-zinc-900/80 backdrop-blur-sm shadow-lg focus-within:border-yellow-600/40 focus-within:ring-1 focus-within:ring-yellow-600/20 transition-all duration-200">
          <Search className="w-5 h-5 text-zinc-500 ml-4 flex-shrink-0" />
          <input
            type="text"
            aria-label="Search stores"
            placeholder="Search stores, cities, or games..."
            value={query}
            onChange={(e) => {
              const val = e.target.value;
              if (val.length <= MAX_QUERY_LENGTH) {
                setQuery(val);
              }
            }}
            className="flex-1 bg-transparent border-none text-zinc-100 placeholder:text-zinc-500 px-3 py-4 text-base focus:outline-none"
          />
          <button
            type="submit"
            className="mr-2 px-4 py-2 rounded-lg bg-yellow-600 hover:bg-yellow-500 text-zinc-950 font-semibold text-sm transition-colors duration-200"
          >
            Search
          </button>
        </div>
      </form>
      <button
        type="button"
        onClick={handleNearMe}
        className="mt-3 inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-yellow-500 transition-colors duration-200"
      >
        <MapPin className="w-3.5 h-3.5" />
        Or find stores near me
      </button>
    </div>
  );
}
