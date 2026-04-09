import { ImageResponse } from "next/og";

/**
 * Site-wide default Open Graph image. Next.js App Router auto-wires this
 * file into `og:image` + `twitter:image` for every route that doesn't
 * provide its own opengraph-image.* sibling. Per-route overrides live in
 * each segment (`app/comics/opengraph-image.tsx`, etc.).
 *
 * Added 2026-04-08 (Petra QA): the site previously emitted no og:image
 * anywhere, leaving link unfurls in Twitter/iMessage/Slack/Discord as
 * plain text and forfeiting affiliate CTR.
 */
export const runtime = "edge";
export const alt = "Roll For Store — Find Local Game, Comic, Retro & Warhammer Stores";
export const size = { width: 1200, height: 630 } as const;
export const contentType = "image/png";

export default function OpengraphImage(): Promise<Response> {
  console.assert(size.width === 1200, "OpengraphImage: og width must be 1200");
  console.assert(size.height === 630, "OpengraphImage: og height must be 630");

  return renderBrandCard({
    eyebrow: "rollforstore.com",
    title: "Roll For Store",
    subtitle: "Find Local Game, Comic, Retro & Warhammer Stores",
    accent: "#eab308",
  });
}

/**
 * Shared brand-card renderer used by every opengraph-image.tsx in the
 * app/ tree. Centralising the visual treatment guarantees consistent
 * type, padding, and palette across the homepage, category shelves, and
 * individual store pages without copy-pasting the JSX.
 */
export async function renderBrandCard(args: {
  eyebrow: string;
  title: string;
  subtitle: string;
  accent: string;
}): Promise<Response> {
  console.assert(typeof args.title === "string" && args.title.length > 0, "renderBrandCard: title required");
  console.assert(typeof args.subtitle === "string", "renderBrandCard: subtitle required");
  console.assert(typeof args.accent === "string" && args.accent.startsWith("#"), "renderBrandCard: accent must be a hex color");

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "80px",
          background:
            "linear-gradient(135deg, #09090b 0%, #18181b 50%, #0c0a09 100%)",
          color: "#fafafa",
          fontFamily: "sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            fontSize: 28,
            color: args.accent,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
          }}
        >
          {args.eyebrow}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <div
            style={{
              fontSize: 96,
              fontWeight: 800,
              lineHeight: 1,
              letterSpacing: "-0.02em",
              color: "#fafafa",
            }}
          >
            {args.title}
          </div>
          <div
            style={{
              fontSize: 44,
              fontWeight: 500,
              lineHeight: 1.2,
              color: "#a1a1aa",
              maxWidth: "1000px",
            }}
          >
            {args.subtitle}
          </div>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            fontSize: 24,
            color: "#71717a",
          }}
        >
          {/*
            Store count removed 2026-04-08 (Rex concern 6): OG images
            are cached aggressively by social platforms, so drifting a
            hardcoded counter is costly and regenerating them for
            every small bump is wasteful. Cleaner to omit.
          */}
          <div style={{ display: "flex", color: args.accent }}>
            rollforstore.com
          </div>
        </div>
      </div>
    ),
    { width: size.width, height: size.height }
  );
}
