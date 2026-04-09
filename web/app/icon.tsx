import { ImageResponse } from "next/og";

/**
 * Browser tab favicon. Next.js App Router auto-wires this file to
 * `/icon` and injects `<link rel="icon">` into every route. Mirrors
 * the brand palette from `app/opengraph-image.tsx` (zinc/black gradient
 * + yellow accent) so tab, unfurl, and social cards all feel like the
 * same product.
 *
 * Added 2026-04-09: rollforstore was shipping the stock Next.js default
 * favicon (Vercel triangle) in browser tabs, which is both off-brand
 * and a trust signal problem for an affiliate directory.
 */
export const runtime = "edge";
export const size = { width: 32, height: 32 } as const;
export const contentType = "image/png";

export default async function Icon(): Promise<Response> {
  console.assert(size.width === 32, "Icon: width must be 32");
  console.assert(size.height === 32, "Icon: height must be 32");

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background:
            "linear-gradient(135deg, #09090b 0%, #18181b 50%, #0c0a09 100%)",
          color: "#eab308",
          fontSize: 24,
          fontWeight: 800,
          fontFamily: "sans-serif",
          letterSpacing: "-0.05em",
          borderRadius: 6,
        }}
      >
        R
      </div>
    ),
    { ...size },
  );
}
