import "server-only";

export class SiteConfigError extends Error {}

const DEV_DEFAULT_ORIGIN = "http://localhost:3000";

/**
 * The single source of truth for every absolute metadata URL (metadataBase,
 * canonical, sitemap, robots' sitemap reference, JSON-LD). Reusing one helper
 * keeps environments from drifting into inconsistent origins.
 *
 * DOCULENS_SITE_URL is deliberately separate from DOCULENS_API_BASE_URL: the
 * former is the public frontend origin search engines and social crawlers
 * see, the latter is the server-only FastAPI backend and must never appear in
 * client-visible metadata.
 */
export function getSiteUrl(): string {
  const raw = process.env.DOCULENS_SITE_URL;

  if (!raw || !raw.trim()) {
    if (process.env.NODE_ENV !== "production") {
      return DEV_DEFAULT_ORIGIN;
    }
    throw new SiteConfigError(
      "DOCULENS_SITE_URL is not configured on the server."
    );
  }

  let url: URL;
  try {
    url = new URL(raw.trim());
  } catch {
    throw new SiteConfigError("DOCULENS_SITE_URL is not a valid URL.");
  }

  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new SiteConfigError(
      "DOCULENS_SITE_URL must use the http or https scheme."
    );
  }

  return `${url.origin}${url.pathname.replace(/\/+$/, "")}`;
}
