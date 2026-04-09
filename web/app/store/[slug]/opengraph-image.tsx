import { renderBrandCard } from "../../opengraph-image";
import { getStore, getStoreBySlug } from "@/lib/queries";
import { isUuid } from "@/lib/slugs";

/**
 * Per-store dynamic Open Graph image. Next.js App Router invokes this
 * once per unique slug and caches the resulting PNG. The fallback path
 * (unknown slug / null lookup) renders a generic brand card rather than
 * 404'ing the image — the page itself emits the real 404, the OG image
 * just needs to not crash if a crawler hits a stale URL.
 *
 * Added 2026-04-08 (Petra QA): no store page was emitting og:image.
 */
export const runtime = "nodejs";
export const alt = "Local game store on Roll For Store";
export const size = { width: 1200, height: 630 } as const;
export const contentType = "image/png";

interface OgProps {
  params: Promise<{ slug: string }>;
}

export default async function OpengraphImage({ params }: OgProps): Promise<Response> {
  // Next.js 16 App Router: dynamic-segment `params` is a Promise, not
  // a plain object. Must await before use — Rex review 2026-04-08
  // caught that the prior sync access would 500 on the first crawler
  // hit even though the build passed (OG routes are dynamic, not
  // prerendered, so the typecheck never exercised the runtime shape).
  const { slug } = await params;
  console.assert(typeof slug === "string" && slug.length > 0, "store OG: slug required");

  const store = isUuid(slug)
    ? await getStore(slug)
    : await getStoreBySlug(slug);

  if (!store) {
    return renderBrandCard({
      eyebrow: "rollforstore.com",
      title: "Roll For Store",
      subtitle: "Find local game, comic, retro, and Warhammer stores",
      accent: "#eab308",
    });
  }

  const city = store.address.city;
  const state = store.address.state;
  const subtitle = `${city}, ${state} · Game store on Roll For Store`;

  return renderBrandCard({
    eyebrow: "rollforstore.com / store",
    title: store.name,
    subtitle,
    accent: "#eab308",
  });
}
