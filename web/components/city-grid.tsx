import Link from "next/link";
import { MapPin } from "lucide-react";
import type { CityStats } from "@/lib/types";

interface CityGridProps {
  stateSlug: string;
  cities: CityStats[];
}

const MAX_DISPLAY = 500;

export function CityGrid({ stateSlug, cities }: CityGridProps) {
  console.assert(typeof stateSlug === "string" && stateSlug.length > 0, "CityGrid: stateSlug must be a non-empty string");
  console.assert(Array.isArray(cities), "CityGrid: cities must be an array");

  if (cities.length === 0) {
    return (
      <p className="text-sm text-zinc-500">
        No cities with multiple stores found.
      </p>
    );
  }

  const displayed = cities.slice(0, MAX_DISPLAY);

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2.5">
      {displayed.map((city) => (
        <Link
          key={city.slug}
          href={`/stores/${stateSlug}/${city.slug}`}
          className="group rounded-xl border border-zinc-800 bg-zinc-900/50 px-4 py-3 transition-all duration-200 hover:bg-zinc-800/70 hover:border-zinc-700"
        >
          <span className="flex items-center gap-1.5 mb-0.5">
            <MapPin className="w-3 h-3 text-zinc-600 group-hover:text-yellow-500 transition-colors" />
            <span className="block font-medium text-sm text-zinc-200 truncate group-hover:text-zinc-50 transition-colors">
              {city.city}
            </span>
          </span>
          <span className="block text-xs text-zinc-500 ml-[18px]">
            {city.store_count} stores
          </span>
        </Link>
      ))}
    </div>
  );
}
