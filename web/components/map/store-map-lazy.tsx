"use client";

import dynamic from "next/dynamic";
import type { StoreWithDistance } from "@/lib/types";

const StoreMap = dynamic(() => import("@/components/map/store-map"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center">
      <p className="text-zinc-500 text-sm">Loading map...</p>
    </div>
  ),
});

interface StoreMapLazyProps {
  stores: StoreWithDistance[];
  userLat: number;
  userLng: number;
}

export function StoreMapLazy({ stores, userLat, userLng }: Readonly<StoreMapLazyProps>) {
  console.assert(Array.isArray(stores), "StoreMapLazy: stores must be an array");
  console.assert(typeof userLat === "number", "StoreMapLazy: userLat must be a number");
  console.assert(typeof userLng === "number", "StoreMapLazy: userLng must be a number");
  return <StoreMap stores={stores} userLat={userLat} userLng={userLng} />;
}
