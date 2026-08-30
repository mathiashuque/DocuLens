import type { MetadataRoute } from "next";

import { getSiteUrl } from "@/lib/site-config";

// Only durable, public, canonical HTML routes belong here. The current route
// surface has exactly one: the public home page. Uploaded-document routes
// (/documents/[documentId]) are per-user, dynamic, and never public.
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: getSiteUrl(),
    },
  ];
}
