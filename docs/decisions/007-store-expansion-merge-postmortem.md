# ADR-007: feat/store-expansion Merge Drop Post-Mortem

**Date:** 2026-04-09
**Status:** accepted

## Context

The `feat/store-expansion` branch added the comics, retro-games, and warhammer category expansions. The `rollforstore-per-store-meta-descriptions` branch added per-store metadata (unique title + description per store, with title-casing). Both branches were long-lived and developed in parallel.

When `feat/store-expansion` was merged into main, the per-store metadata changes were silently dropped — the merge did not conflict (no overlapping lines), so Git accepted the merge without warning. The loss was not detected until a subsequent code review noticed the metadata was missing.

## Decision

To prevent silent merge drops in the future:

**Verify critical behaviors after every merge of a long-lived branch.** The check is simple: after merging, grep for the known-changed functions or exports and confirm they are present in the merge commit. A missing export is a merge drop; immediately revert or re-apply the changes.

**run_sync.sh loud-failure fix:** The data pipeline's `run_sync.sh` was updated to fail loudly (non-zero exit, clear error message) if any expected output file or database row is absent after a sync step. This makes the equivalent problem (a pipeline step silently dropping its output) immediately visible in logs rather than discovered during the next QA pass.

**Broader lesson:** Long-lived branches in a fast-moving repo accumulate silent conflict risk. Prefer short-lived branches, frequent rebases, or feature flags to keep branch lifetimes under 2 days.

## Consequences

- Per-store metadata was re-applied on the `feat/lgs-seo-batch-2` branch and merged to main on 2026-04-09.
- `run_sync.sh` now asserts expected output is present after each step.
- Code review checklist updated: after any merge, verify that expected functions/exports from the source branch are present in the merge commit.

## Notes

- Reference incident: `feat/store-expansion` merge, detected during `rollforstore-per-store-meta-descriptions` apply.
- See also `web/docs/seo-decisions.md` — Known SEO Issues / History section (references this incident as "feat/store-expansion merge: dropped the per-store meta changes — always check for this pattern when merging long-lived branches").
- See ADR-002 for the redirect-in-Suspense incident (same pattern: correct code, wrong location — detected by Petra's curl-based QA).
