#!/usr/bin/env bash
# LGS Directory — Weekly New Sources Discovery Sync
# Runs via systemd timer (lgs-new-sources-sync.timer)
# Scrapes Games Workshop, comic stores, and retro game stores
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

echo "=== New Sources Discovery Sync — $(date) ==="

# 1. Games Workshop retailer locator
if [ "${LGS_ENABLE_GW_DISCOVERY:-1}" = "1" ]; then
  echo "--- Games Workshop Discovery ---"
  lgs discover games-workshop --verbose || echo "GW discovery failed, continuing..."
fi

# 2. Comic book stores (League of Comic Geeks)
if [ "${LGS_ENABLE_COMIC_DISCOVERY:-1}" = "1" ]; then
  echo "--- Comic Store Discovery ---"
  lgs discover comics --verbose || echo "Comic discovery failed, continuing..."
fi

# 3. Retro video game stores
if [ "${LGS_ENABLE_RETRO_DISCOVERY:-1}" = "1" ]; then
  echo "--- Retro Game Store Discovery ---"
  lgs discover retro-games --verbose || echo "Retro discovery failed, continuing..."
fi

# 4. Auto-categorize from website content
echo "--- Auto-Categorize ---"
lgs discover auto-categorize --verbose || echo "Auto-categorize failed, continuing..."

# 5. Validate newly discovered candidates
echo "--- Validate New Candidates ---"
lgs validate run --status candidate --limit 500 || echo "Validation failed, continuing..."

# 6. Content scraping for new stores
echo "--- Content Scraping ---"
lgs scrape content --limit 200 || echo "Content scraping failed, continuing..."

# 7. Match newly discovered stores to Google Place IDs
echo "--- Google Place ID Matching ---"
lgs enrich match-google --limit 500 || echo "Google match-google failed, continuing..."

# 8. Google Places enrichment for newly matched stores
echo "--- Google Places Enrichment ---"
lgs enrich google --limit 200 || echo "Google enrichment failed, continuing..."

echo "=== New Sources Discovery Sync Complete — $(date) ==="
