"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StoreStatusBadge, WpnBadge } from "@/components/status-badge";
import { formatCityState, formatDistance } from "@/lib/format";
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

export default function NearMePage() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [stores, setStores] = useState<StoreWithDistance[]>([]);
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(
    null
  );
  const [radius, setRadius] = useState("25");

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
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Near Me</h1>
          <p className="text-sm text-zinc-500">
            Find local game stores close to your location
          </p>
        </div>
        <div className="flex items-center gap-3">
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
          <Button
            onClick={handleLocate}
            disabled={phase === "locating" || phase === "loading"}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            {phase === "locating"
              ? "Locating..."
              : phase === "loading"
                ? "Searching..."
                : "Find Stores"}
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
              Click &ldquo;Find Stores&rdquo; to search near your location
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
                  href={`/store/${store.id}`}
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
