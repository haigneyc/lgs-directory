-- Create the city_descriptions table for AI-generated city descriptions.
-- Phase 2 of programmatic SEO pages.
-- Safe to re-run (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS city_descriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  state VARCHAR(50) NOT NULL,
  city VARCHAR(100) NOT NULL,
  description TEXT NOT NULL,
  generated_at TIMESTAMP DEFAULT NOW(),
  model VARCHAR(50) NOT NULL,
  UNIQUE(state, city)
);

-- Index for the most common lookup pattern: fetch description by state + city.
CREATE INDEX IF NOT EXISTS idx_city_descriptions_state_city
  ON city_descriptions (state, city);
