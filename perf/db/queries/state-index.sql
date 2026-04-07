-- getStateIndex() — full aggregation over stores grouped by state.
SELECT address->>'state' AS state, COUNT(*)::int AS store_count
FROM stores
WHERE status IN ('active', 'verified', 'candidate')
  AND address->>'state' IS NOT NULL
GROUP BY address->>'state'
ORDER BY store_count DESC;
