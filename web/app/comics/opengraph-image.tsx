import { renderBrandCard } from "../opengraph-image";

export const runtime = "edge";
export const alt = "Comic Shops on Roll For Store";
export const size = { width: 1200, height: 630 } as const;
export const contentType = "image/png";

export default function OpengraphImage(): Promise<Response> {
  console.assert(size.width === 1200, "comics OG: width must be 1200");
  console.assert(size.height === 630, "comics OG: height must be 630");
  return renderBrandCard({
    eyebrow: "rollforstore.com / comics",
    title: "Comic Shops",
    subtitle: "New releases, back issues, and graphic novels near you",
    accent: "#22d3ee",
  });
}
