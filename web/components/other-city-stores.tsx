import Link from "next/link";
import type { Store } from "@/lib/types";

interface OtherCityStoresProps {
  stores: Store[];
  cityName: string;
  stateSlug: string;
  citySlug: string;
}

const MAX_DISPLAY = 6;

export function OtherCityStores({ stores, cityName, stateSlug, citySlug }: OtherCityStoresProps) {
  console.assert(Array.isArray(stores), "OtherCityStores: stores must be an array");
  console.assert(typeof cityName === "string" && cityName.length > 0, "OtherCityStores: cityName must be non-empty");

  if (stores.length === 0) {
    return null;
  }

  const displayed = stores.slice(0, MAX_DISPLAY);

  return (
    <section className="border-t border-zinc-800/60 pt-8 mb-8">
      <h2 className="font-display font-semibold text-zinc-200 mb-4">
        Other Stores in {cityName}
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {displayed.map((store) => (
          <Link
            key={store.id}
            href={`/store/${store.id}`}
            className="rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-3 hover:bg-zinc-800/60 transition-colors"
          >
            <p className="text-sm font-medium text-zinc-200 truncate">{store.name}</p>
            <p className="text-xs text-zinc-500 mt-0.5 truncate">{store.address.street}</p>
          </Link>
        ))}
      </div>
      <div className="mt-4">
        <Link
          href={`/stores/${stateSlug}/${citySlug}`}
          className="text-sm text-yellow-500 hover:text-yellow-400 transition-colors"
        >
          View all stores in {cityName} &rarr;
        </Link>
      </div>
    </section>
  );
}
