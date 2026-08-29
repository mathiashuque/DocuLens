import "server-only";

import { analysisSchema, type Analysis } from "./analysis-schema";
import { getBackendBaseUrl } from "./backend-config";
import { BackendError } from "./errors";
import { parseJsonSafely } from "./http";

const REQUEST_TIMEOUT_MS = 30_000;

/**
 * Retrieves the completed analysis for one document, or `null` when none
 * exists yet (FastAPI 404 — this never means the document itself is
 * missing, since callers only call this once the document has loaded).
 * Never invokes the analysis provider: this is a plain read. Used only
 * from Server Components/route handlers — never imported into client
 * bundles.
 */
export async function fetchAnalysis(documentId: string): Promise<Analysis | null> {
  const baseUrl = getBackendBaseUrl();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(
      `${baseUrl}/api/documents/${encodeURIComponent(documentId)}/analysis`,
      { method: "GET", cache: "no-store", signal: controller.signal }
    );
  } catch {
    throw new BackendError(
      "unavailable",
      "The analysis service is currently unavailable."
    );
  } finally {
    clearTimeout(timeout);
  }

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new BackendError(
      "unavailable",
      "The analysis service returned an unexpected error.",
      response.status
    );
  }

  const body = await parseJsonSafely(response);
  const result = analysisSchema.safeParse(body);
  if (!result.success) {
    throw new BackendError(
      "malformed_response",
      "The analysis service returned an unexpected response."
    );
  }

  return result.data;
}

export type AnalysisLoadResult =
  | { status: "none" }
  | { status: "ready"; analysis: Analysis }
  | { status: "error"; message: string };

/**
 * Page-facing wrapper around `fetchAnalysis` that never throws: "no
 * completed analysis yet" and "the analysis service failed" are both
 * expected, safely renderable page states, never a page-level 404/500.
 */
export async function loadAnalysis(documentId: string): Promise<AnalysisLoadResult> {
  try {
    const analysis = await fetchAnalysis(documentId);
    return analysis === null ? { status: "none" } : { status: "ready", analysis };
  } catch (error) {
    const message =
      error instanceof BackendError
        ? error.message
        : "The analysis could not be loaded.";
    return { status: "error", message };
  }
}
