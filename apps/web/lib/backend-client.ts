import "server-only";

import { getBackendBaseUrl } from "./backend-config";
import { documentSchema, type Document } from "./document-schema";
import { BackendError } from "./errors";

const REQUEST_TIMEOUT_MS = 30_000;

async function parseJsonSafely(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return undefined;
  }
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

/**
 * Retrieves one persisted document from FastAPI. Used only from Server
 * Components/route handlers — never imported into client bundles.
 */
export async function fetchDocument(documentId: string): Promise<Document> {
  const baseUrl = getBackendBaseUrl();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(
      `${baseUrl}/api/documents/${encodeURIComponent(documentId)}`,
      { method: "GET", cache: "no-store", signal: controller.signal }
    );
  } catch {
    throw new BackendError(
      "unavailable",
      "The document service is currently unavailable."
    );
  } finally {
    clearTimeout(timeout);
  }

  // A malformed ID fails FastAPI's UUID path validation (422); treat it the
  // same as "not found" since neither case has a document to show.
  if (response.status === 404 || response.status === 422) {
    throw new BackendError("not_found", "Document not found.", response.status);
  }

  if (!response.ok) {
    throw new BackendError(
      "unavailable",
      "The document service returned an unexpected error.",
      response.status
    );
  }

  const body = await parseJsonSafely(response);
  const result = documentSchema.safeParse(body);
  if (!result.success) {
    throw new BackendError(
      "malformed_response",
      "The document service returned an unexpected response."
    );
  }

  return result.data;
}
