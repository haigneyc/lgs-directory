#!/usr/bin/env bash
# LGS Directory — Weekly Google Discovery Sync
# Runs via systemd timer (lgs-google-sync.timer)
# Rotates through 8 grid shards — full US coverage in 8 weeks
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

SHARD_COUNT="${LGS_GOOGLE_SHARD_COUNT:-8}"
MAX_REQUESTS="${LGS_GOOGLE_MAX_REQUESTS:-3000}"
DETAIL_TIER="${LGS_GOOGLE_DETAIL_TIER:-enterprise}"
STATE_FILE="data/state/google-shard-index"

# Read current shard index (0-based)
mkdir -p data/state
SHARD_INDEX=0
if [ -f "$STATE_FILE" ]; then
  SHARD_INDEX=$(cat "$STATE_FILE")
fi

echo "=== Google Discovery Sync — $(date) ==="
echo "Shard: ${SHARD_INDEX}/${SHARD_COUNT}, Max requests: ${MAX_REQUESTS}"

# Run Google Places discovery for this shard
lgs discover google \
  --shard-index "$SHARD_INDEX" \
  --shard-count "$SHARD_COUNT" \
  --max-requests "$MAX_REQUESTS" \
  --detail-tier "$DETAIL_TIER" \
  ${LGS_GOOGLE_SKIP_KNOWN_IDS:+--skip-known-ids}

# Advance shard index on success
NEXT_SHARD=$(( (SHARD_INDEX + 1) % SHARD_COUNT ))
echo "$NEXT_SHARD" > "$STATE_FILE"
echo "Next shard: ${NEXT_SHARD}"

# Enrich newly discovered stores with Google Places data
echo "--- Enriching new discoveries ---"
lgs enrich google --limit 100 || echo "Enrichment failed, continuing..."

echo "=== Google Discovery Sync Complete — $(date) ==="
