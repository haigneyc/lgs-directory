"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import Link from "next/link";
import { formatCityState, formatDistance } from "@/lib/format";
import { storeHref } from "@/lib/slugs";
import type { StoreWithDistance } from "@/lib/types";
import "leaflet/dist/leaflet.css";

// Fix Leaflet default marker icon (broken in bundlers)
const defaultIcon = L.icon({
  iconUrl: "/leaflet/marker-icon.png",
  iconRetinaUrl: "/leaflet/marker-icon-2x.png",
  shadowUrl: "/leaflet/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const userIcon = L.icon({
  iconUrl: "/leaflet/marker-icon.png",
  iconRetinaUrl: "/leaflet/marker-icon-2x.png",
  shadowUrl: "/leaflet/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
  className: "hue-rotate-180 brightness-150",
});

L.Marker.prototype.options.icon = defaultIcon;

function FitBounds({
  stores,
  userLat,
  userLng,
}: {
  stores: StoreWithDistance[];
  userLat: number;
  userLng: number;
}) {
  const map = useMap();

  useEffect(() => {
    const points: L.LatLngExpression[] = [
      [userLat, userLng],
      ...stores
        .filter((s) => s.latitude !== null && s.longitude !== null)
        .map((s) => [s.latitude!, s.longitude!] as L.LatLngExpression),
    ];
    if (points.length > 1) {
      map.fitBounds(L.latLngBounds(points), { padding: [40, 40] });
    }
  }, [map, stores, userLat, userLng]);

  return null;
}

interface StoreMapProps {
  stores: StoreWithDistance[];
  userLat: number;
  userLng: number;
}

export default function StoreMap({
  stores,
  userLat,
  userLng,
}: StoreMapProps) {
  return (
    <MapContainer
      center={[userLat, userLng]}
      zoom={10}
      className="h-full w-full rounded-lg"
      style={{ minHeight: "400px" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitBounds stores={stores} userLat={userLat} userLng={userLng} />

      {/* User location marker */}
      <Marker position={[userLat, userLng]} icon={userIcon}>
        <Popup>
          <span className="font-medium">Your location</span>
        </Popup>
      </Marker>

      {/* Store markers */}
      {stores.map((store) => {
        if (store.latitude === null || store.longitude === null) return null;
        return (
          <Marker
            key={store.id}
            position={[store.latitude, store.longitude]}
            icon={defaultIcon}
          >
            <Popup>
              <div className="text-sm">
                <Link
                  href={storeHref(store)}
                  className="font-medium text-blue-600 hover:underline"
                >
                  {store.name}
                </Link>
                <p className="text-gray-600">
                  {formatCityState(store.address)}
                </p>
                <p className="text-gray-500">
                  {formatDistance(store.distance_miles)}
                </p>
              </div>
            </Popup>
          </Marker>
        );
      })}
    </MapContainer>
  );
}
