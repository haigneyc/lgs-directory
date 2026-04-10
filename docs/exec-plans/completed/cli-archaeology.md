# CLI Archaeology — Restored Pipeline Lifecycle

**Status:** completed
**Shipped:** 2026-04-10
**Owner:** Soren

## Context

The Python data pipeline had several lifecycle commands that had been broken or removed over time. This work restored the full lifecycle: validate → enrich → freshness checks. Also added shard rotation for the Google Places weekly grid scan, `last_validated` timestamp writes on validation, and loud failures (non-zero exit + stderr) instead of silent continues.

## Acceptance criteria

- [x] `lifecycle/` module restored: validate, retire, freshness commands functional
- [x] `enrich/` module restored and wired to daily sync
- [x] Shard rotation implemented for Google Places weekly grid scan (8 shards)
- [x] `last_validated` timestamp written on every successful store validation
- [x] Pipeline exits non-zero on fatal errors (no more silent failures)

## What shipped

Shipped 2026-04-10. Daily sync now covers the full store lifecycle. Loud failures mean broken pipeline runs surface in systemd journal instead of silently completing with data rot.
