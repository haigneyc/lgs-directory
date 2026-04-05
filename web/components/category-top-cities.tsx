import Link from "next/link";
import { stateToSlug, cityToSlug } from "@/lib/slugs";

interface CategoryTopCitiesProps {
  categoryLabel: string;
  cities: { city: string; state: string; store_count: number }[];
}

const MAX_DISPLAY = 10;

export function CategoryTopCities({ categoryLabel, cities }: CategoryTopCitiesProps) {
  console.assert(Array.isArray(cities), "CategoryTopCities: cities must be an array");
  console.assert(typeof categoryLabel === "string" && categoryLabel.length > 0, "CategoryTopCities: categoryLabel must be non-empty");

  if (cities.length === 0) {
    return null;
  }

  const displayed = cities.slice(0, MAX_DISPLAY);

  return (
    <section className="mt-8">
      <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-3">
        Top Cities for {categoryLabel}
      </h2>
      <div className="flex flex-wrap gap-2">
        {displayed.map((c) => (
          <Link
            key={`${c.city}-${c.state}`}
            href={`/stores/${stateToSlug(c.state)}/${cityToSlug(c.city)}`}
            className="rounded-md bg-zinc-800 px-3 py-1.5 text-sm text-zinc-400 hover:bg-zinc-700 transition-colors"
          >
            {c.city}, {c.state} ({c.store_count})
          </Link>
        ))}
      </div>
    </section>
  );
}
