-- getPopularCities(12) — GROUP BY city, state with trusted candidate filter.
SELECT
  address->>'city' AS city,
  address->>'state' AS state,
  COUNT(*)::int AS store_count
FROM stores
WHERE status IN ('active', 'verified', 'candidate')
  AND NOT (
    status = 'candidate'
    AND wpn_id IS NULL
    AND id NOT IN (
      SELECT store_id FROM store_external_refs
      WHERE provider = 'website_content'
        AND jsonb_array_length(COALESCE(payload->'products', '[]'::jsonb)) > 0
    )
  )
  AND address->>'city' IS NOT NULL
  AND address->>'state' IS NOT NULL
GROUP BY address->>'city', address->>'state'
ORDER BY store_count DESC
LIMIT 12;
