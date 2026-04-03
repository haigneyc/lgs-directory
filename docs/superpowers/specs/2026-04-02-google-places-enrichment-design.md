# Google Places Enrichment — Design Spec

**Date:** 2026-04-02
**Author:** Kira (Architect) + Chris
**Project:** lgs-directory
**Status:** Approved

---

## Overview

Enrich store records with Google Places data (business hours, rating, photos) to make directory pages more useful and improve SEO. Two-phase rollout: enrich existing stores with Google Place IDs immediately (~170 stores), then enrich new stores automatically as the weekly discovery pipeline finds them.

**Cost estimate:** ~$1.36 for initial 170-store enrichment. Ongoing cost folded into existing weekly Google discovery budget.

---

## Storage

Enrichment data stored in the existing `store_external_refs` table.

**Table:** `store_external_refs`
- `store_id` (FK → stores.id)
- `provider` = `'google_places'`
- `external_id` = Google Place ID
- `payload` (JSONB) — enrichment data goes here
- `last_seen` — updated on each enrichment pass

**Payload schema:**

```json
{
  "hours": {
    "weekday_text": [
      "Monday: 10:00 AM – 8:00 PM",
      "Tuesday: 10:00 AM – 8:00 PM",
      "Wednesday: 10:00 AM – 8:00 PM",
      "Thursday: 10:00 AM – 8:00 PM",
      "Friday: 10:00 AM – 9:00 PM",
      "Saturday: 10:00 AM – 6:00 PM",
      "Sunday: Closed"
    ],
    "periods": [
      { "open": { "day": 1, "hour": 10, "minute": 0 }, "close": { "day": 1, "hour": 20, "minute": 0 } }
    ]
  },
  "rating": 4.2,
  "user_rating_count": 156,
  "photo_refs": [
    "places/ChIJxxx/photos/AUc7tXXX"
  ],
  "enriched_at": "2026-04-02T15:30:00Z"
}
```

**No migration needed** — table and columns already exist.

---

## Backend Pipeline (Python)

### New CLI Command: `lgs enrich google`

**Location:** `src/lgs_directory/cli/enrich.py` (new file)

**Behavior:**
1. Query stores that have a `google_place_id` AND either:
   - No `store_external_refs` row with `provider = 'google_places'`, OR
   - Existing row where `payload->>'enriched_at'` is older than 30 days
2. For each store, call Google Places API Place Details (New) endpoint:
   - URL: `https://places.googleapis.com/v1/places/{placeId}`
   - Field mask: `regularOpeningHours,rating,userRatingCount,photos`
   - Header: `X-Goog-Api-Key: {GOOGLE_PLACES_API_KEY}`
   - Header: `X-Goog-FieldMask: regularOpeningHours,rating,userRatingCount,photos`
3. Parse response, build payload JSON
4. Upsert into `store_external_refs`:
   - If row exists for (provider='google_places', external_id=place_id): update payload + last_seen
   - If not: insert new row
5. Log progress: `[42/170] Enriched "Pat's Games" — rating: 4.2, hours: 7 days, photos: 3`

**Rate limiting:** 10 requests/second (Google's default QPS for Place Details)

**Error handling:**
- 404 (place not found): skip, log warning
- 429 (rate limited): back off 5 seconds, retry up to 3 times
- Other errors: skip, log error, continue to next store

**CLI options:**
- `--dry-run` — show what would be enriched without calling the API
- `--limit N` — cap the number of stores to enrich (for testing)
- `--force` — re-enrich all stores regardless of `enriched_at` age

### Integration with Weekly Discovery Pipeline

**File to modify:** `scripts/run_google_sync.sh`

After the existing discovery step, add:
```bash
lgs enrich google --limit 100
```

This enriches up to 100 newly discovered stores per weekly run. Combined with the 30-day staleness check, all stores with Place IDs will be enriched and refreshed over time.

---

## Frontend Integration (Next.js)

### New Query Function

**File:** `web/lib/queries.ts`

```typescript
interface StoreEnrichment {
  hours_weekday_text: string[] | null;
  rating: number | null;
  user_rating_count: number | null;
  photo_refs: string[] | null;
  enriched_at: string | null;
}

export async function getStoreEnrichment(storeId: string): Promise<StoreEnrichment | null>
```

SQL:
```sql
SELECT payload FROM store_external_refs
WHERE store_id = $1 AND provider = 'google_places'
LIMIT 1
```

Parse the JSONB payload into the `StoreEnrichment` interface. Return null if no row found. Wrap in try/catch for graceful degradation (same pattern as `getCityDescription`).

### Store Detail Page (`/store/[id]`)

Add enrichment data to the store detail page:

**Hours section** (if `hours_weekday_text` is available):
- Render as a simple list below the store info cards
- Each day on its own line: "Monday: 10:00 AM – 8:00 PM"
- Styled: `text-sm text-zinc-400`
- Section header: "Hours" with `text-xs uppercase tracking-wider text-zinc-500`

**Rating badge** (if `rating` is available):
- Show next to the store name or in the info cards
- Format: "★ 4.2 (156 reviews)"
- Styled: amber-400 for the star, zinc-400 for the count

**Photos** (if `photo_refs` is available):
- Show a "View on Google Maps" link that opens the store's Google Maps page
- URL: `https://www.google.com/maps/place/?q=place_id:{google_place_id}`
- Do NOT embed Google Photos directly (licensing/cost concerns)

### City Page Store Table

Add a rating column to the store table on city pages (if enrichment data is available):

- New optional column: "Rating"
- Shows "★ 4.2" or "—" if no rating
- Only show the column if at least one store in the list has a rating

This requires fetching enrichment data for all stores on the page. To avoid N+1 queries, add a batch query:

```typescript
export async function getStoreEnrichments(storeIds: string[]): Promise<Map<string, StoreEnrichment>>
```

SQL:
```sql
SELECT store_id, payload FROM store_external_refs
WHERE store_id = ANY($1) AND provider = 'google_places'
```

### Formatting Utilities

**File:** `web/lib/format.ts`

Add:
- `formatRating(rating: number, count: number)` → "★ 4.2 (156)"
- `formatHoursToday(weekdayText: string[])` → "Open until 8:00 PM" or "Closed" based on current day

---

## Cost Analysis

**Initial enrichment (Part A):**
- ~170 stores with Google Place IDs
- Contact fields (hours): $3/1000 = $0.51
- Atmosphere fields (rating, photos): $5/1000 = $0.85
- **Total: ~$1.36**

**Ongoing (Part C):**
- Weekly discovery finds ~20-50 new stores with Place IDs
- Enrichment adds ~$0.10-0.25/week to existing Google API costs
- 30-day refresh cycle: ~170 re-enrichments/month = ~$1.36/month

---

## What's NOT In Scope

- Downloading or hosting Google Photos (licensing, storage cost)
- Google Reviews text (noisy, storage-heavy, low SEO value)
- Matching all 5,500 stores to Google Place IDs (separate future effort)
- Real-time hours checking ("open now" badge) — would need client-side timezone logic
