import { ImageResponse } from "next/og";

/**
 * iOS home-screen / Safari pinned-tab icon. Next.js App Router auto-
 * wires this file to `/apple-icon` and injects
 * `<link rel="apple-touch-icon">`. Extra inner padding accounts for
 * iOS's rounded-rectangle mask so the "R" glyph isn't clipped.
 *
 * Shares palette with `app/icon.tsx` and `app/opengraph-image.tsx`.
 */
export const runtime = "edge";
export const size = { width: 180, height: 180 } as const;
export const contentType = "image/png";

export default async function AppleIcon(): Promise<Response> {
  console.assert(size.width === 180, "AppleIcon: width must be 180");
  console.assert(size.height === 180, "AppleIcon: height must be 180");

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
          fontSize: 128,
          fontWeight: 800,
          fontFamily: "sans-serif",
          letterSpacing: "-0.05em",
          padding: 24,
        }}
      >
        R
      </div>
    ),
    { ...size },
  );
}
