"use client";

import dynamic from "next/dynamic";

const DetailMap = dynamic(() => import("@/components/map/detail-map"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center">
      <p className="text-zinc-500 text-sm">Loading map...</p>
    </div>
  ),
});

interface DetailMapLazyProps {
  latitude: number;
  longitude: number;
  storeName: string;
}

export function DetailMapLazy({ latitude, longitude, storeName }: Readonly<DetailMapLazyProps>) {
  console.assert(typeof latitude === "number" && !Number.isNaN(latitude), "DetailMapLazy: latitude must be a valid number");
  console.assert(typeof longitude === "number" && !Number.isNaN(longitude), "DetailMapLazy: longitude must be a valid number");
  console.assert(typeof storeName === "string" && storeName.length > 0, "DetailMapLazy: storeName must be a non-empty string");
  return <DetailMap latitude={latitude} longitude={longitude} storeName={storeName} />;
}
