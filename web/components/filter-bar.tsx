"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState, useCallback } from "react";
import { Search, X } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { formatCategory } from "@/lib/format";
import { Button } from "@/components/ui/button";

interface FilterBarProps {
  states: string[];
  statuses: string[];
  wpnLevels: string[];
  categories: string[];
}

export function FilterBar({ states, statuses, wpnLevels, categories }: FilterBarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  console.assert(Array.isArray(states), "FilterBar: states must be an array");
  console.assert(Array.isArray(categories), "FilterBar: categories must be an array");

  const setParam = useCallback(
    (key: string, value: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value && value !== "all") {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      params.delete("page"); // Reset to page 1 on filter change
      router.push(`/?${params.toString()}`);
    },
    [router, searchParams]
  );

  const currentState = searchParams.get("state") ?? "";
  const currentStatus = searchParams.get("status") ?? "";
  const currentWpn = searchParams.get("wpn") ?? "";
  const currentCategory = searchParams.get("category") ?? "";
  const currentSearch = searchParams.get("q") ?? "";
  const [searchText, setSearchText] = useState(currentSearch);

  const submitSearch = useCallback(() => {
    const trimmed = searchText.trim();
    setParam("q", trimmed || null);
  }, [searchText, setParam]);

  const hasFilters = currentState || currentStatus || currentWpn || currentCategory || currentSearch;

  return (
    <div className="flex flex-wrap items-center gap-2.5">
      <div className="flex items-center gap-1.5">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
          <Input
            placeholder="Search stores..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="w-52 pl-9 bg-zinc-900/80 border-zinc-800 text-zinc-50 placeholder:text-zinc-500 rounded-lg focus:border-yellow-600/40 focus:ring-yellow-600/20"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                submitSearch();
              }
            }}
          />
        </div>
        <Button
          variant="outline"
          size="icon"
          className="bg-zinc-900/80 border-zinc-800 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg"
          onClick={submitSearch}
          aria-label="Search"
        >
          <Search className="size-4" />
        </Button>
      </div>

      <Select
        value={currentState || "all"}
        onValueChange={(v) => setParam("state", v)}
      >
        <SelectTrigger className="w-32 bg-zinc-900/80 border-zinc-800 text-zinc-300 rounded-lg">
          <SelectValue placeholder="State" />
        </SelectTrigger>
        <SelectContent className="bg-zinc-900 border-zinc-800">
          <SelectItem value="all" className="text-zinc-400">
            All states
          </SelectItem>
          {states.map((s) => (
            <SelectItem key={s} value={s} className="text-zinc-200">
              {s}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={currentStatus || "all"}
        onValueChange={(v) => setParam("status", v)}
      >
        <SelectTrigger className="w-36 bg-zinc-900/80 border-zinc-800 text-zinc-300 rounded-lg">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent className="bg-zinc-900 border-zinc-800">
          <SelectItem value="all" className="text-zinc-400">
            All statuses
          </SelectItem>
          {statuses.map((s) => (
            <SelectItem key={s} value={s} className="text-zinc-200">
              {s}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={currentWpn || "all"}
        onValueChange={(v) => setParam("wpn", v)}
      >
        <SelectTrigger className="w-36 bg-zinc-900/80 border-zinc-800 text-zinc-300 rounded-lg">
          <SelectValue placeholder="WPN Level" />
        </SelectTrigger>
        <SelectContent className="bg-zinc-900 border-zinc-800">
          <SelectItem value="all" className="text-zinc-400">
            All WPN levels
          </SelectItem>
          {wpnLevels.map((w) => (
            <SelectItem key={w} value={w} className="text-zinc-200">
              {w}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={currentCategory || "all"}
        onValueChange={(v) => setParam("category", v)}
      >
        <SelectTrigger className="w-40 bg-zinc-900/80 border-zinc-800 text-zinc-300 rounded-lg">
          <SelectValue placeholder="Category" />
        </SelectTrigger>
        <SelectContent className="bg-zinc-900 border-zinc-800">
          <SelectItem value="all" className="text-zinc-400">
            All categories
          </SelectItem>
          {categories.map((c) => (
            <SelectItem key={c} value={c} className="text-zinc-200">
              {formatCategory(c)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {hasFilters && (
        <Button
          variant="ghost"
          size="sm"
          className="text-zinc-500 hover:text-zinc-300 gap-1"
          onClick={() => router.push("/")}
        >
          <X className="w-3.5 h-3.5" />
          Clear
        </Button>
      )}
    </div>
  );
}
