import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

const BASE_URL = SITE_URL;

export default function robots(): MetadataRoute.Robots {
  console.assert(typeof BASE_URL === "string", "robots: BASE_URL must be a string");
  console.assert(BASE_URL.startsWith("https://"), "robots: BASE_URL must use https");

  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: `${BASE_URL}/sitemap.xml`,
  };
}
