import type { MetadataRoute } from "next";

import { SUPPORTED_LOCALES } from "@/lib/i18n/locales";
import { getSiteUrl } from "@/lib/site-config";

// robots.txt is a crawl-budget hint, not access control: uploaded-document
// and API paths are also marked noindex at the route level (see
// app/[lang]/documents/[documentId]/layout.tsx), because some crawlers
// ignore disallow rules while still respecting per-page robots meta. Every
// locale's document path is disallowed explicitly rather than relying on a
// prefix-free pattern, since locale segments are a real part of the path.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [...SUPPORTED_LOCALES.map((locale) => `/${locale}/documents/`), "/api/"],
    },
    sitemap: `${getSiteUrl()}/sitemap.xml`,
  };
}
