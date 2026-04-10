# Roll For Store — Agent Entry Point

Roll For Store is a US local game store directory at **rollforstore.com**. It covers LGS (MTG ecosystem), comic shops, retro game stores, and Warhammer/miniatures hobby shops.

> **Important**: This is Next.js 16 with Cache Components — APIs differ from your training data. Read `node_modules/next/dist/docs/` before writing any Next.js code. `cacheLife`/`cacheTag` are stable (no `unstable_` prefix). `cacheComponents: true` in `next.config.ts` enables Cache Components.

## Quick Reference — Where to Look

| Topic | File |
|-------|------|
| Tech stack, URL structure, trust filter, DB connection, key lib files | [docs/architecture.md](docs/architecture.md) |
| SEO decisions: slugs, soft-404, JSON-LD, OG images, metadata | [docs/seo-decisions.md](docs/seo-decisions.md) |
| Architecture Decision Records (why we built things this way) | [../docs/decisions/](../docs/decisions/) |
| Python data pipeline (WPN, Google Places, scraping, enrichment) | [docs/pipeline.md](docs/pipeline.md) |
| Full CLI reference for `lgs` commands | [../docs/cli_reference.md](../docs/cli_reference.md) |
| Product requirements (MVP scope) | [../docs/prd.md](../docs/prd.md) |
| Phase 2 product requirements | [../docs/phase2_prd.md](../docs/phase2_prd.md) |
| Active work plans, completed history, backlog | [../docs/exec-plans/](../docs/exec-plans/) |

## Stack at a Glance

- **Framework**: Next.js 16, React 19, TypeScript (strict)
- **Styling**: Tailwind v4, shadcn/ui (Base UI + Radix)
- **Database**: `@neondatabase/serverless` → Supabase Supavisor pooler
- **Cache**: Next.js 16 Cache Components (`'use cache'`, `cacheLife`, `cacheTag`)
- **Deployment**: Vercel Pro

## Critical Constraints (Read Before Touching Anything)

These cause real damage if missed:

1. **Never commit or push without Chris's explicit approval.** Stage with `git add .` when done.
2. **Always branch from main.** Branch names: `feat/`, `fix/`, `perf/`, `seo/`, `refactor/`.
3. **Minimum 2 runtime assertions per function** — not just TypeScript types. Use `console.assert(...)` with a descriptive message.
4. **All loops must have fixed upper bounds** — no unbounded iteration.
5. **Zero warnings policy** — all ESLint and TypeScript warnings resolved before presenting work.
6. **All return values checked** — every non-void return value inspected; every function validates its parameters.
7. **Do NOT use `export const revalidate`** — conflicts with Cache Components. Use `cacheLife()`/`cacheTag()` inside `'use cache'` functions instead.
8. **Trust filter must remain in `listStores`** — `TRUSTED_CANDIDATE_FILTER` in `lib/queries.ts` prevents junk candidates from appearing publicly.
9. **Slug-based store URLs** — stores live at `/store/[slug]`, not `/store/[uuid]`. UUID paths → 308 redirect.
10. **Soft-404 for missing stores** — call `notFound()`, never return 200 with empty content.
11. **Max 3 DB connections per instance** — defined in `lib/db.ts`. Do not increase without benchmarking.

## Dev Setup (Fast Path)

```bash
# Install dependencies
bun install

# Start dev server
bun dev

# Lint + type check
bun run lint
tsc --noEmit
```

## Verify Before Presenting

- `bun run lint` — zero errors, zero warnings
- `tsc --noEmit` — zero type errors
- Check that Cache Components annotations (`'use cache'`, `cacheLife`, `cacheTag`) are correct on any new data functions
