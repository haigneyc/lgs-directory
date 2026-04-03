import Link from "next/link";
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
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
      {displayed.map((city) => (
        <Link
          key={city.slug}
          href={`/stores/${stateSlug}/${city.slug}`}
          className="rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-800"
        >
          <span className="block font-medium truncate">{city.city}</span>
          <span className="block text-xs text-zinc-500">
            {city.store_count} stores
          </span>
        </Link>
      ))}
    </div>
  );
}
