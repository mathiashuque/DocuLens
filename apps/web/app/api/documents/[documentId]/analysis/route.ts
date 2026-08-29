import { NextResponse, type NextRequest } from "next/server";

import { BackendConfigError, getBackendBaseUrl } from "@/lib/backend-config";
import { anonymousHeader, anonymousSessionFor, applyAnonymousCookie } from "@/lib/anonymous-session";

export const runtime = "nodejs";

const REQUEST_TIMEOUT_MS = 60_000;

function safeErrorResponse(status: number, error: string, message: string) {
  return NextResponse.json({ error, message }, { status });
}

function extractDetail(body: unknown): string | undefined {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
  }
  return undefined;
}

type RouteContext = { params: Promise<{ documentId: string }> };

/**
 * Same-origin proxy for the user-triggered analysis POST. Forwards only the
 * document ID in the path — no client body, headers, or cookies — and never
 * retries, since a retry could spend a second round of provider tokens after
 * a failure that already completed on the backend.
 */
export async function POST(request: NextRequest, { params }: RouteContext) {
  const { documentId } = await params;
  let anonymousSession: ReturnType<typeof anonymousSessionFor>;
  try { anonymousSession = anonymousSessionFor(request); } catch { return safeErrorResponse(502, "server_configuration", "Usage protection is not configured."); }

  let baseUrl: string;
  try {
    baseUrl = getBackendBaseUrl();
  } catch (error) {
    if (error instanceof BackendConfigError) {
      return safeErrorResponse(
        502,
        "server_configuration",
        "The analysis service is not configured."
      );
    }
    throw error;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(
      `${baseUrl}/api/documents/${encodeURIComponent(documentId)}/analysis`,
      { method: "POST", headers: anonymousHeader(anonymousSession), signal: controller.signal }
    );
  } catch {
    return safeErrorResponse(
      502,
      "upstream_unavailable",
      "The analysis service is currently unavailable."
    );
  } finally {
    clearTimeout(timeout);
  }

  const rawBody = await response.text();
  let parsedBody: unknown;
  try {
    parsedBody = rawBody ? JSON.parse(rawBody) : undefined;
  } catch {
    return safeErrorResponse(
      502,
      "upstream_malformed",
      "The analysis service returned an unexpected response."
    );
  }

  if (response.status === 201) {
    return applyAnonymousCookie(NextResponse.json(parsedBody, { status: 201 }), anonymousSession);
  }

  if (response.status === 429) {
    const retryAt = parsedBody && typeof parsedBody === "object" && "retry_at" in parsedBody ? (parsedBody as { retry_at?: unknown }).retry_at : null;
    return applyAnonymousCookie(NextResponse.json({ error: "quota_exceeded", message: "Your daily analysis allowance is exhausted. Precomputed demos remain available.", retry_at: typeof retryAt === "string" ? retryAt : null }, { status: 429 }), anonymousSession);
  }

  if (response.status === 404) {
    return safeErrorResponse(404, "not_found", "Document not found.");
  }

  if (response.status === 409) {
    return safeErrorResponse(
      409,
      "textless_document",
      extractDetail(parsedBody) ??
        "This document has no extracted text available to analyze."
    );
  }

  if (response.status === 503) {
    return safeErrorResponse(
      503,
      "provider_unavailable",
      "The analysis provider is currently unavailable."
    );
  }

  if (response.status === 502) {
    return safeErrorResponse(
      502,
      "provider_invalid",
      "The analysis provider failed to produce a valid result."
    );
  }

  return safeErrorResponse(
    502,
    "upstream_error",
    "The analysis service returned an unexpected error."
  );
}
