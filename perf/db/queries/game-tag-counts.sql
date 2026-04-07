-- getGameTagCounts() — LATERAL jsonb_array_elements_text over
-- store_external_refs payload->'products'. Expensive; scales poorly.
SELECT elem AS tag, COUNT(DISTINCT store_id)::int AS count
FROM store_external_refs,
     LATERAL jsonb_array_elements_text(payload->'products') AS elem
WHERE provider = 'website_content'
GROUP BY elem
ORDER BY count DESC;
