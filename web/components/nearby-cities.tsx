import Link from "next/link";
import type { CityStats } from "@/lib/types";

interface NearbyCitiesProps {
  stateSlug: string;
  cities: CityStats[];
}

const MAX_DISPLAY = 8;

export function NearbyCities({ stateSlug, cities }: NearbyCitiesProps) {
  console.assert(typeof stateSlug === "string" && stateSlug.length > 0, "NearbyCities: stateSlug must be a non-empty string");
  console.assert(Array.isArray(cities), "NearbyCities: cities must be an array");

  if (cities.length === 0) {
    return null;
  }

  const displayed = cities.slice(0, MAX_DISPLAY);

  return (
    <section>
      <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-3">
        Nearby Cities
      </h2>
      <div className="flex flex-wrap gap-2">
        {displayed.map((city) => (
          <Link
            key={city.slug}
            href={`/stores/${stateSlug}/${city.slug}`}
            className="rounded-md bg-zinc-800 px-3 py-1.5 text-sm text-zinc-400 hover:bg-zinc-700"
          >
            {city.city} ({city.store_count})
          </Link>
        ))}
      </div>
    </section>
  );
}
