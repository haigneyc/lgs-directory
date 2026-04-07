-- getNearbyStores(33.94, -118.40, 25, 50) — bounding box + Haversine.
-- lat delta = 25/69 ≈ 0.3623; lng delta = 25/(69*cos(33.94°)) ≈ 0.4369.
SELECT id, name, address, latitude, longitude, status,
  3959 * 2 * ASIN(SQRT(
    POWER(SIN(RADIANS(latitude - 33.94) / 2), 2) +
    COS(RADIANS(33.94)) * COS(RADIANS(latitude)) *
    POWER(SIN(RADIANS(longitude - (-118.40)) / 2), 2)
  )) AS distance_miles
FROM stores
WHERE status IN ('active', 'verified', 'candidate')
  AND latitude IS NOT NULL
  AND longitude IS NOT NULL
  AND latitude BETWEEN 33.5777 AND 34.3023
  AND longitude BETWEEN -118.8369 AND -117.9631
ORDER BY distance_miles
LIMIT 50;
