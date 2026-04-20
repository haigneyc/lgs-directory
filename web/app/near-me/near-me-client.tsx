"use client";

import { useState, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StoreStatusBadge, WpnBadge } from "@/components/status-badge";
import { formatCityState, formatDistance } from "@/lib/format";
import { storeHref } from "@/lib/slugs";
import type { StoreWithDistance } from "@/lib/types";

// Leaflet must be loaded client-side only (requires window)
const StoreMap = dynamic(() => import("@/components/map/store-map"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full rounded-lg bg-zinc-900 flex items-center justify-center">
      <p className="text-zinc-500">Loading map...</p>
    </div>
  ),
});

type Phase = "idle" | "locating" | "loading" | "done" | "error";

interface NominatimResult {
  lat: string;
  lon: string;
}

const NOMINATIM_URL = "https://nominatim.openstreetmap.org/search";
const NOMINATIM_USER_AGENT = "RollForStore/1.0";
const MAX_QUERY_LENGTH = 200;

async function geocodeLocation(
  locationQuery: string
): Promise<{ lat: number; lng: number } | null> {
  console.assert(
    typeof locationQuery === "string",
    "geocodeLocation: locationQuery must be a string"
  );
  console.assert(
    locationQuery.length > 0 && locationQuery.length <= MAX_QUERY_LENGTH,
    "geocodeLocation: locationQuery must be between 1 and 200 characters"
  );

  const params = new URLSearchParams({
    q: locationQuery,
    format: "json",
    countrycodes: "us",
    limit: "1",
  });

  const res = await fetch(`${NOMINATIM_URL}?${params.toString()}`, {
    headers: { "User-Agent": NOMINATIM_USER_AGENT },
  });

  if (!res.ok) {
    return null;
  }

  const data: NominatimResult[] = await res.json();

  console.assert(Array.isArray(data), "geocodeLocation: response must be an array");

  if (data.length === 0) {
    return null;
  }

  const lat = parseFloat(data[0].lat);
  const lng = parseFloat(data[0].lon);

  if (isNaN(lat) || isNaN(lng)) {
    return null;
  }

  return { lat, lng };
}

export interface NearMeClientProps {
  initialLat: number | null;
  initialLng: number | null;
  initialCity: string | null;
  initialState: string | null;
}

/**
 * Seed the location input with "City, ST" when the server passed us a
 * Vercel-geo-derived city. Users can clear it before searching; this
 * just skips the manual step when we already know roughly where they
 * are.
 */
function initialLocationQuery(
  city: string | null,
  state: string | null
): string {
  if (city === null || city.length === 0) return "";
  if (state === null || state.length === 0) return city;
  return `${city}, ${state}`;
}

export default function NearMeClient(props: NearMeClientProps) {
  console.assert(typeof props === "object" && props !== null, "NearMeClient: props required");
  console.assert(
    props.initialLat === null || Number.isFinite(props.initialLat),
    "NearMeClient: initialLat must be null or finite"
  );

  const [phase, setPhase] = useState<Phase>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [stores, setStores] = useState<StoreWithDistance[]>([]);
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(
    null
  );
  const [radius, setRadius] = useState("25");
  const [locationQuery, setLocationQuery] = useState(() =>
    initialLocationQuery(props.initialCity, props.initialState)
  );
  const [isGeocoding, setIsGeocoding] = useState(false);
  const locationInputRef = useRef<HTMLInputElement>(null);

  const fetchNearby = useCallback(
    async (lat: number, lng: number, r: string) => {
      setPhase("loading");
      const res = await fetch(
        `/api/stores/nearby?lat=${lat}&lng=${lng}&radius=${r}&limit=50`
      );
      if (!res.ok) {
        setPhase("error");
        setErrorMsg("Failed to fetch nearby stores");
        return;
      }
      const data: StoreWithDistance[] = await res.json();
      setStores(data);
      setPhase("done");
    },
    []
  );

  const handleLocate = useCallback(() => {
    if (!navigator.geolocation) {
      setPhase("error");
      setErrorMsg("Geolocation is not supported by your browser");
      return;
    }

    setPhase("locating");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setCoords({ lat, lng });
        fetchNearby(lat, lng, radius);
      },
      (err) => {
        setPhase("error");
        setErrorMsg(
          err.code === 1
            ? "Location access denied. Please enable location permissions."
            : "Unable to determine your location"
        );
      },
      { enableHighAccuracy: false, timeout: 10000 }
    );
  }, [radius, fetchNearby]);

  const handleLocationSearch = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      const trimmed = locationQuery.trim();
      if (trimmed.length === 0) {
        return;
      }

      console.assert(
        trimmed.length <= MAX_QUERY_LENGTH,
        "handleLocationSearch: query must not exceed max length"
      );
      console.assert(
        typeof trimmed === "string",
        "handleLocationSearch: trimmed must be a string"
      );

      setIsGeocoding(true);
      setPhase("loading");
      setErrorMsg("");

      const result = await geocodeLocation(trimmed);

      if (result === null) {
        setIsGeocoding(false);
        setPhase("error");
        setErrorMsg(
          "Location not found. Try a different city or zip code."
        );
        return;
      }

      setIsGeocoding(false);
      setCoords({ lat: result.lat, lng: result.lng });
      fetchNearby(result.lat, result.lng, radius);
    },
    [locationQuery, radius, fetchNearby]
  );

  const handleRadiusChange = useCallback(
    (r: string | null) => {
      if (!r) return;
      setRadius(r);
      if (coords) {
        fetchNearby(coords.lat, coords.lng, r);
      }
    },
    [coords, fetchNearby]
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 h-[calc(100vh-3.5rem)]">
      <div className="mb-4 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-zinc-300">
              Search by location
            </h2>
            <p className="text-sm text-zinc-500">
              Enter a city, zip code, or use precise browser location to find tabletop gaming, TCG, and hobby stores.
            </p>
          </div>
          <Select value={radius} onValueChange={handleRadiusChange}>
            <SelectTrigger className="w-28 bg-zinc-900 border-zinc-800 text-zinc-300">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-zinc-900 border-zinc-800">
              <SelectItem value="10" className="text-zinc-200">
                10 miles
              </SelectItem>
              <SelectItem value="25" className="text-zinc-200">
                25 miles
              </SelectItem>
              <SelectItem value="50" className="text-zinc-200">
                50 miles
              </SelectItem>
              <SelectItem value="100" className="text-zinc-200">
                100 miles
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
          <form
            onSubmit={handleLocationSearch}
            className="flex flex-1 items-center gap-2"
          >
            <Input
              ref={locationInputRef}
              type="text"
              placeholder="Enter city, state or zip code"
              value={locationQuery}
              onChange={(e) => {
                const val = e.target.value;
                if (val.length <= MAX_QUERY_LENGTH) {
                  setLocationQuery(val);
                }
              }}
              className="flex-1 bg-zinc-900 border-zinc-800 text-zinc-200 placeholder:text-zinc-500"
            />
            <Button
              type="submit"
              disabled={
                isGeocoding ||
                phase === "loading" ||
                locationQuery.trim().length === 0
              }
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {isGeocoding ? "Searching..." : "Search"}
            </Button>
          </form>

          <span className="hidden sm:block text-xs text-zinc-600 px-2">
            or
          </span>
          <div className="flex items-center justify-center sm:hidden">
            <span className="text-xs text-zinc-600">&mdash; or &mdash;</span>
          </div>

          <Button
            onClick={handleLocate}
            disabled={phase === "locating" || phase === "loading"}
            variant="outline"
            className="border-zinc-800 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
          >
            {phase === "locating" ? "Locating..." : "Use My Location"}
          </Button>
        </div>
      </div>

      {phase === "error" && (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {errorMsg}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 h-[calc(100%-5rem)]">
        {/* Map */}
        <div className="lg:col-span-2 rounded-lg border border-zinc-800 overflow-hidden bg-zinc-900 min-h-[400px]">
          {phase === "idle" ? (
            <div className="h-full flex items-center justify-center text-zinc-500">
              Search by location or use your current position to find nearby stores
            </div>
          ) : coords ? (
            <StoreMap
              stores={stores}
              userLat={coords.lat}
              userLng={coords.lng}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-zinc-500">
              Determining your location...
            </div>
          )}
        </div>

        {/* Results sidebar */}
        <div className="overflow-y-auto rounded-lg border border-zinc-800 bg-zinc-950">
          {phase === "done" && stores.length === 0 && (
            <div className="p-6 text-center text-zinc-500">
              No stores found within {radius} miles.
            </div>
          )}
          {phase === "done" && stores.length > 0 && (
            <div className="divide-y divide-zinc-800">
              <div className="px-4 py-3 text-sm text-zinc-500">
                {stores.length} store{stores.length !== 1 ? "s" : ""} within{" "}
                {radius} mi
              </div>
              {stores.map((store) => (
                <Link
                  key={store.id}
                  href={storeHref(store)}
                  className="block px-4 py-3 hover:bg-zinc-900/50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-medium text-sm text-zinc-50 truncate">
                        {store.name}
                      </p>
                      <p className="text-xs text-zinc-500 mt-0.5">
                        {formatCityState(store.address)}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1 flex-shrink-0">
                      <span className="text-xs font-mono text-zinc-400">
                        {formatDistance(store.distance_miles)}
                      </span>
                      <div className="flex gap-1">
                        <StoreStatusBadge status={store.status} />
                        <WpnBadge level={store.wpn_level} />
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
          {(phase === "idle" || phase === "locating" || phase === "loading") &&
            stores.length === 0 && (
              <div className="p-6 text-center text-zinc-600 text-sm">
                {phase === "idle"
                  ? "Results will appear here"
                  : "Searching..."}
              </div>
            )}
        </div>
      </div>
    </div>
  );
}
