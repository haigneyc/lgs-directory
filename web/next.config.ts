import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable Next.js 16 Cache Components (Partial Prerendering) so pages can
  // mix a static prerendered shell with dynamic `'use cache'`-backed data
  // holes. Required for PERF-027 — pairs with `'use cache'` directives on
  // read functions in `lib/queries.ts` and the removal of every
  // `export const revalidate = …` across `app/`.
  cacheComponents: true,
};

export default nextConfig;
