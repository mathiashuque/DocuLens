import "server-only";

export class BackendConfigError extends Error {}

/**
 * DOCULENS_API_BASE_URL must stay server-only (no NEXT_PUBLIC_ prefix): it
 * points at the FastAPI origin and must never reach the browser bundle.
 */
export function getBackendBaseUrl(): string {
  const raw = process.env.DOCULENS_API_BASE_URL;
  if (!raw || !raw.trim()) {
    throw new BackendConfigError(
      "DOCULENS_API_BASE_URL is not configured on the server."
    );
  }

  let url: URL;
  try {
    url = new URL(raw.trim());
  } catch {
    throw new BackendConfigError("DOCULENS_API_BASE_URL is not a valid URL.");
  }

  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new BackendConfigError(
      "DOCULENS_API_BASE_URL must use the http or https scheme."
    );
  }

  return `${url.origin}${url.pathname.replace(/\/+$/, "")}`;
}
