import { renderBrandCard } from "../opengraph-image";

export const runtime = "edge";
export const alt = "Retro Game Stores on Roll For Store";
export const size = { width: 1200, height: 630 } as const;
export const contentType = "image/png";

export default function OpengraphImage(): Promise<Response> {
  console.assert(size.width === 1200, "retro OG: width must be 1200");
  console.assert(size.height === 630, "retro OG: height must be 630");
  return renderBrandCard({
    eyebrow: "rollforstore.com / retro",
    title: "Retro Game Stores",
    subtitle: "Classic consoles, cartridges, and vintage gaming",
    accent: "#f97316",
  });
}
