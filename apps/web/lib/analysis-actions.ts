import { parseAnalysis, type Analysis } from "./analysis-schema";

export type TriggerAnalysisFailureKind =
  | "not_found"
  | "conflict"
  | "provider_unavailable"
  | "provider_invalid"
  | "malformed_response"
  | "unavailable";

export type TriggerAnalysisResult =
  | { ok: true; analysis: Analysis }
  | { ok: false; kind: TriggerAnalysisFailureKind; message: string };

function extractMessage(body: unknown): string | undefined {
  if (body && typeof body === "object" && "message" in body) {
    const message = (body as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }
  return undefined;
}

/**
 * Submits the user-triggered analyze action to the same-origin route
 * handler, which forwards it to FastAPI. Never retries automatically: a
 * retry could spend a second round of provider tokens after a failure that
 * already completed on the backend.
 */
export async function triggerAnalysis(
  documentId: string,
  signal?: AbortSignal
): Promise<TriggerAnalysisResult> {
  let response: Response;
  try {
    response = await fetch(
      `/api/documents/${encodeURIComponent(documentId)}/analysis`,
      { method: "POST", signal }
    );
  } catch {
    return {
      ok: false,
      kind: "unavailable",
      message:
        "Could not reach the analysis service. Check your connection and try again.",
    };
  }

  const text = await response.text();
  let body: unknown;
  try {
    body = text ? JSON.parse(text) : undefined;
  } catch {
    return {
      ok: false,
      kind: "malformed_response",
      message: "The analysis service returned an unexpected response.",
    };
  }

  if (response.status === 201) {
    const result = parseAnalysis(body);
    if (!result.success) {
      return {
        ok: false,
        kind: "malformed_response",
        message: "The analysis service returned an unexpected response.",
      };
    }
    return { ok: true, analysis: result.data };
  }

  if (response.status === 404) {
    return {
      ok: false,
      kind: "not_found",
      message: extractMessage(body) ?? "This document could not be found.",
    };
  }

  if (response.status === 409) {
    return {
      ok: false,
      kind: "conflict",
      message:
        extractMessage(body) ??
        "This document has no extracted text available to analyze.",
    };
  }

  if (response.status === 503) {
    return {
      ok: false,
      kind: "provider_unavailable",
      message:
        extractMessage(body) ??
        "The analysis provider is currently unavailable. Try again shortly.",
    };
  }

  if (response.status === 502) {
    return {
      ok: false,
      kind: "provider_invalid",
      message:
        extractMessage(body) ??
        "The analysis provider failed to produce a usable result.",
    };
  }

  return {
    ok: false,
    kind: "unavailable",
    message: "Something went wrong starting analysis. Please try again.",
  };
}
