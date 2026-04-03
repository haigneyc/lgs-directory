#!/usr/bin/env bash
# LGS Directory — Daily Sync Pipeline
# Runs via systemd timer (lgs-sync.timer)
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

echo "=== LGS Daily Sync — $(date) ==="

# 1. WPN recrawl
if [ "${LGS_ENABLE_WPN_RECRAWL:-1}" = "1" ]; then
  echo "--- WPN Recrawl ---"
  lgs discover wpn || echo "WPN recrawl failed, continuing..."
fi

# 2. Validate candidates (web presence + platform + singles)
echo "--- Validate Candidates ---"
lgs validate run --status candidate --limit "${LGS_VALIDATE_CANDIDATE_LIMIT:-250}" || echo "Candidate validation failed, continuing..."

# 3. Validate verified stores
echo "--- Validate Verified ---"
lgs validate run --status verified --limit "${LGS_VALIDATE_VERIFIED_LIMIT:-250}" || echo "Verified validation failed, continuing..."

# 4. Health checks
echo "--- Health Checks ---"
lgs lifecycle health --limit "${LGS_HEALTH_LIMIT:-1000}" || echo "Health checks failed, continuing..."

# 5. Closure detection
if [ "${LGS_ENABLE_CLOSURE_CHECK:-1}" = "1" ]; then
  echo "--- Closure Detection ---"
  lgs lifecycle closure-check --limit "${LGS_CLOSURE_LIMIT:-500}" || echo "Closure detection failed, continuing..."
fi

# 6. Freshness checks
echo "--- Freshness Checks ---"
lgs freshness run --limit "${LGS_FRESHNESS_LIMIT:-250}" || echo "Freshness checks failed, continuing..."

# 7. Content scraping (free — HTTP only, no API cost)
echo "--- Content Scraping ---"
lgs scrape content --limit 200 || echo "Content scraping failed, continuing..."

# 8. Google Places enrichment (~$0.05/run for stale refreshes)
echo "--- Google Places Enrichment ---"
lgs enrich google --limit 50 || echo "Google enrichment failed, continuing..."

echo "=== Daily Sync Complete — $(date) ==="
