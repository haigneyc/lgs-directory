#!/usr/bin/env bash
# LGS Directory — Daily Sync Pipeline
# Runs via systemd timer (lgs-sync.timer)
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

echo "=== LGS Daily Sync — $(date) ==="

FAILED_STEPS=""

# 1. WPN recrawl
if [ "${LGS_ENABLE_WPN_RECRAWL:-1}" = "1" ]; then
  echo "--- WPN Recrawl ---"
  lgs discover wpn || { echo "STEP 1 (WPN recrawl) FAILED with exit $?"; FAILED_STEPS="${FAILED_STEPS}wpn-recrawl "; }
fi

# 2. Validate candidates (web presence + platform + singles)
echo "--- Validate Candidates ---"
lgs validate run --status candidate --limit "${LGS_VALIDATE_CANDIDATE_LIMIT:-250}" || { echo "STEP 2 (validate candidates) FAILED with exit $?"; FAILED_STEPS="${FAILED_STEPS}validate-candidates "; }

# 3. Validate verified stores
echo "--- Validate Verified ---"
lgs validate run --status verified --limit "${LGS_VALIDATE_VERIFIED_LIMIT:-250}" || { echo "STEP 3 (validate verified) FAILED with exit $?"; FAILED_STEPS="${FAILED_STEPS}validate-verified "; }

# 4. Health checks
echo "--- Health Checks ---"
lgs lifecycle health --limit "${LGS_HEALTH_LIMIT:-1000}" || { echo "STEP 4 (health checks) FAILED with exit $?"; FAILED_STEPS="${FAILED_STEPS}health-checks "; }

# 5. Closure detection
if [ "${LGS_ENABLE_CLOSURE_CHECK:-1}" = "1" ]; then
  echo "--- Closure Detection ---"
  lgs lifecycle closure-check --limit "${LGS_CLOSURE_LIMIT:-500}" || { echo "STEP 5 (closure detection) FAILED with exit $?"; FAILED_STEPS="${FAILED_STEPS}closure-detection "; }
fi

# 6. Freshness checks
echo "--- Freshness Checks ---"
lgs freshness run --limit "${LGS_FRESHNESS_LIMIT:-250}" || { echo "STEP 6 (freshness checks) FAILED with exit $?"; FAILED_STEPS="${FAILED_STEPS}freshness-checks "; }

# 7. Content scraping (free — HTTP only, no API cost)
echo "--- Content Scraping ---"
lgs scrape content --limit 200 || { echo "STEP 7 (content scraping) FAILED with exit $?"; FAILED_STEPS="${FAILED_STEPS}content-scraping "; }

# 8. Match unmatched stores to Google Place IDs
echo "--- Google Place ID Matching ---"
lgs enrich match-google --limit 200 || { echo "STEP 8 (google match) FAILED with exit $?"; FAILED_STEPS="${FAILED_STEPS}google-match "; }

# 9. Google Places enrichment (~$0.05/run for stale refreshes)
echo "--- Google Places Enrichment ---"
lgs enrich google --limit 50 || { echo "STEP 9 (google enrich) FAILED with exit $?"; FAILED_STEPS="${FAILED_STEPS}google-enrich "; }

echo "=== Daily Sync Complete — $(date) ==="
if [ -n "${FAILED_STEPS}" ]; then
  echo "SYNC FAILURES: ${FAILED_STEPS}"
  exit 1
fi
