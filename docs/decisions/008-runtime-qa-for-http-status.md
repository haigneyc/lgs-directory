# ADR-008: Runtime QA Required for HTTP-Status Work

**Date:** 2026-04-09
**Status:** accepted

## Context

During the slug migration (2026-04-08, commit `a610836`), `resolveSlugParam` correctly called `permanentRedirect(storeSlugPath(...))` — the right Next.js helper. Rex code-reviewed the change twice and confirmed the helper usage was correct. In production, `curl -I /store/<uuid>` returned `HTTP/2 200` instead of `308`.

Root cause: `resolveSlugParam` was invoked from a Server Component nested inside a `<Suspense>` boundary. By the time the redirect threw, the streaming shell had already started and the HTTP status was committed at 200. The browser still navigated to the slug URL via client-side `router.replace()`, so browser-based QA passed. Only Googlebot (no JS) saw the 200 — and indexed UUID URLs as live pages, directly defeating the slug migration's purpose of transferring ranking signal.

## Decision

For any work involving URL routing, redirects, middleware/proxy, canonical handling, or rewrites: code review alone is insufficient. After Soren reports done and Rex approves, dispatch Petra with explicit `curl -sI` verification of HTTP status codes.

Specify exact curl commands in the dispatch prompt:
```
curl -sI https://www.rollforstore.com/store/<uuid> | head -5
# Expect: HTTP/2 308 and location: header pointing to slug URL
```

The `-I` flag (headers only, no follow) is critical — `-L` follows redirects and hides the status you need to verify. Browser navigation is also insufficient because client-side `router.replace()` masks server-status bugs.

The reverse also holds: HTTP-status-only QA misses hydration, layout, and content bugs. Pair both Petra (curl-based) and browser-based QA for redirect work.

**The fix for this incident:** Moved the redirect from the Server Component into `proxy.ts` (Next.js middleware), where it runs before streaming begins. Middleware executes before any rendering; the HTTP status is never committed before the redirect fires.

## Consequences

- All redirect work in this repo goes through proxy.ts (middleware layer).
- QA checklist for any URL-routing change: Petra must verify with curl, not just browser navigation.
- Code review is necessary but not sufficient for HTTP-layer behavior.

## Notes

- See `web/lib/proxy.ts` for the middleware-layer redirect implementation.
- See `/home/chris/.claude/projects/-home-chris-jarvis/memory/feedback_runtime_qa_catches_http_bugs.md` for the full incident context.
- This pattern applies to all of Chris's Next.js projects, not just rollforstore.
