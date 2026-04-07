-- listStores({ state: 'CA' }) — JSONB state filter + trusted candidate filter.
SELECT id, name, address, latitude, longitude, status, wpn_level, discovery_source
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
  AND address->>'state' = 'CA'
ORDER BY name
LIMIT 25 OFFSET 0;
