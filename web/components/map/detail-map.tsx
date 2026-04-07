"use client";

import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
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

L.Marker.prototype.options.icon = defaultIcon;

interface DetailMapProps {
  latitude: number;
  longitude: number;
  storeName: string;
}

export default function DetailMap({
  latitude,
  longitude,
  storeName,
}: DetailMapProps) {
  console.assert(
    typeof latitude === "number" && !Number.isNaN(latitude),
    "DetailMap: latitude must be a valid number"
  );
  console.assert(
    typeof longitude === "number" && !Number.isNaN(longitude),
    "DetailMap: longitude must be a valid number"
  );

  return (
    <MapContainer
      center={[latitude, longitude]}
      zoom={14}
      className="h-full w-full rounded-lg"
      style={{ minHeight: "256px" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Marker position={[latitude, longitude]} icon={defaultIcon}>
        <Popup>
          <span className="font-medium">{storeName}</span>
        </Popup>
      </Marker>
    </MapContainer>
  );
}
