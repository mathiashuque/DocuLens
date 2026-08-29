import { NextResponse, type NextRequest } from "next/server";

import { BackendConfigError, getBackendBaseUrl } from "@/lib/backend-config";

export const runtime = "nodejs";

const REQUEST_TIMEOUT_MS = 60_000;
const KNOWN_UPSTREAM_ERROR_STATUSES = new Set([400, 413, 415, 422]);

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

/**
 * Same-origin proxy for document creation. Forwards only the `file` field
 * to FastAPI — no client headers or cookies — and never retries, since a
 * retry after a partial failure could create a duplicate persisted document.
 */
export async function POST(request: NextRequest) {
  let baseUrl: string;
  try {
    baseUrl = getBackendBaseUrl();
  } catch (error) {
    if (error instanceof BackendConfigError) {
      return safeErrorResponse(
        502,
        "server_configuration",
        "The document service is not configured."
      );
    }
    throw error;
  }

  let incomingForm: FormData;
  try {
    incomingForm = await request.formData();
  } catch {
    return safeErrorResponse(
      400,
      "invalid_request",
      "The request body must be a multipart form."
    );
  }

  const file = incomingForm.get("file");
  if (!(file instanceof File)) {
    return safeErrorResponse(400, "invalid_request", "A PDF file is required.");
  }

  const outgoingForm = new FormData();
  outgoingForm.set("file", file, file.name);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/documents`, {
      method: "POST",
      body: outgoingForm,
      signal: controller.signal,
    });
  } catch {
    return safeErrorResponse(
      502,
      "upstream_unavailable",
      "The document service is currently unavailable."
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
      "The document service returned an unexpected response."
    );
  }

  if (response.status === 201) {
    return NextResponse.json(parsedBody, { status: 201 });
  }

  if (KNOWN_UPSTREAM_ERROR_STATUSES.has(response.status)) {
    return safeErrorResponse(
      response.status,
      "upload_rejected",
      extractDetail(parsedBody) ?? "The document could not be uploaded."
    );
  }

  return safeErrorResponse(
    502,
    "upstream_error",
    "The document service returned an unexpected error."
  );
}
