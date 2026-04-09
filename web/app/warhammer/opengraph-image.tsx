import { renderBrandCard } from "../opengraph-image";

export const runtime = "edge";
export const alt = "Warhammer & Hobby Stores on Roll For Store";
export const size = { width: 1200, height: 630 } as const;
export const contentType = "image/png";

export default function OpengraphImage(): Promise<Response> {
  console.assert(size.width === 1200, "warhammer OG: width must be 1200");
  console.assert(size.height === 630, "warhammer OG: height must be 630");
  return renderBrandCard({
    eyebrow: "rollforstore.com / warhammer",
    title: "Warhammer & Hobby Stores",
    subtitle: "Miniatures, paints, and tabletop wargaming near you",
    accent: "#f59e0b",
  });
}
