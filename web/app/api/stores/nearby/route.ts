import { NextRequest } from "next/server";
import { getNearbyStores } from "@/lib/queries";

export async function GET(request: NextRequest) {
  const sp = request.nextUrl.searchParams;
  const lat = parseFloat(sp.get("lat") ?? "");
  const lng = parseFloat(sp.get("lng") ?? "");
  const radius = parseFloat(sp.get("radius") ?? "25");
  const limit = parseInt(sp.get("limit") ?? "50", 10);

  if (isNaN(lat) || isNaN(lng)) {
    return Response.json(
      { error: "lat and lng query parameters are required" },
      { status: 400 }
    );
  }

  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
    return Response.json(
      { error: "lat must be [-90,90] and lng must be [-180,180]" },
      { status: 400 }
    );
  }

  const clampedRadius = Math.min(Math.max(radius, 1), 200);
  const clampedLimit = Math.min(Math.max(limit, 1), 200);

  const stores = await getNearbyStores(lat, lng, clampedRadius, clampedLimit);

  return Response.json(stores);
}
