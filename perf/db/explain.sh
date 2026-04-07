#!/usr/bin/env bash
# EXPLAIN ANALYZE benchmark runner for the representative rollforstore queries.
# Uses psql against a read-only replica. Outputs a single JSON array file with
# one entry per query: {"name": "...", "plan": <json-explain>}.
#
# Required env: DATABASE_URL must point to a read-only role with
# statement_timeout set conservatively (30s recommended).
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL must be set}"

QUERIES_DIR="$(dirname "$0")/queries"
OUT_DIR="$(dirname "$0")/results"
mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/results-$(date -u +%Y%m%dT%H%M%SZ).json"

echo "[" > "$OUT"
first=1
# Bounded loop — at most 50 query files.
count=0
for f in "$QUERIES_DIR"/*.sql; do
  count=$((count + 1))
  if [ "$count" -gt 50 ]; then
    echo "explain.sh: refusing to run more than 50 queries" >&2
    exit 1
  fi
  name=$(basename "$f" .sql)
  plan=$(psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -At -c "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) $(cat "$f")")
  if [ "$first" -eq 0 ]; then
    echo "," >> "$OUT"
  fi
  printf '{"name":"%s","plan":%s}' "$name" "$plan" >> "$OUT"
  first=0
done
echo "" >> "$OUT"
echo "]" >> "$OUT"

echo "Wrote $OUT"
