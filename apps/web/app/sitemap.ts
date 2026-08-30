import type { MetadataRoute } from "next";

import { SUPPORTED_LOCALES } from "@/lib/i18n/locales";
import { getSiteUrl } from "@/lib/site-config";

// Only durable, public, canonical HTML routes belong here. The current route
// surface has exactly one per locale: the public localized home page.
// Uploaded-document routes (/[lang]/documents/[documentId]) are per-user,
// dynamic, and never public.
export default function sitemap(): MetadataRoute.Sitemap {
  const siteUrl = getSiteUrl();
  const languages = Object.fromEntries(SUPPORTED_LOCALES.map((locale) => [locale, `${siteUrl}/${locale}`]));

  return SUPPORTED_LOCALES.map((locale) => ({
    url: `${siteUrl}/${locale}`,
    alternates: { languages },
  }));
}
