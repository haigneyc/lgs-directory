# LGS Pipeline — scrape.py AssertionError at cli/scrape.py:165

**Status:** active
**Priority:** P2 (pipeline reliability)
**Owner:** Soren

## Context

An `AssertionError` at `cli/scrape.py:165` (or equivalent in the LGS pipeline) was surfaced during sync runs on 2026-04-08. The assertion likely fires when a store record has a missing or unexpected `store_id` value. The same bug exists in the LFS repo (see `lfs-locator/docs/exec-plans/active/scrape-store-id-bug.md`). This needs a targeted fix: add a guard before the assertion or ensure the upstream data always satisfies the assertion's precondition.

## Acceptance criteria

- [ ] Reproduce the AssertionError by running the scrape command against a store with a null/unexpected store_id
- [ ] Add a pre-assertion guard (skip or log-and-continue) so the pipeline doesn't crash on malformed records
- [ ] Verify the fix does not silently drop valid stores
- [ ] `ruff check` and `mypy` pass with zero warnings after the fix
- [ ] Daily sync run completes without AssertionError

## Notes

- **Inferred from today's sync run logs — verify exact file/line before fixing**
- The same pattern exists in lfs-locator; fix both repos together if the code is shared
- Do not remove the assertion entirely — log the offending record and continue instead
- Related files: Python pipeline `cli/scrape.py` (or equivalent path in lgs-directory)
