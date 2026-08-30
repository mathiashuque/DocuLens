import type { MetadataRoute } from "next";

import { getSiteUrl } from "@/lib/site-config";

// robots.txt is a crawl-budget hint, not access control: uploaded-document
// and API paths are also marked noindex at the route level (see
// app/documents/[documentId]/layout.tsx), because some crawlers ignore
// disallow rules while still respecting per-page robots meta.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/documents/", "/api/"],
    },
    sitemap: `${getSiteUrl()}/sitemap.xml`,
  };
}
