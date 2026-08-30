import type { Dictionary } from "./i18n/dictionary";
import { parseDocument, type Document } from "./document-schema";

export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
export const ACCEPTED_CONTENT_TYPE = "application/pdf";

export type UploadResult =
  | { ok: true; document: Document }
  | { ok: false; message: string };

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
 * Submits one PDF to the same-origin Next.js route handler, which forwards
 * it to FastAPI. Never retries automatically: a retry after a partial
 * failure could create a duplicate persisted document. Failure messages are
 * frontend-owned copy from `dict`, since the backend does not localize its
 * free-form error text.
 */
export async function uploadDocument(
  file: File,
  dict: Dictionary["upload"],
  signal?: AbortSignal
): Promise<UploadResult> {
  const formData = new FormData();
  formData.set("file", file);

  let response: Response;
  try {
    response = await fetch("/api/documents", {
      method: "POST",
      body: formData,
      signal,
    });
  } catch {
    return { ok: false, message: dict.errorNetwork };
  }

  const text = await response.text();
  let body: unknown;
  try {
    body = text ? JSON.parse(text) : undefined;
  } catch {
    return { ok: false, message: dict.errorUnexpectedResponse };
  }

  if (response.status === 201) {
    const result = parseDocument(body);
    if (!result.success) {
      return { ok: false, message: dict.errorUnexpectedResponse };
    }
    return { ok: true, document: result.data };
  }

  if (response.status === 413) {
    return { ok: false, message: dict.errorTooLargeServer };
  }
  if (response.status === 415) {
    return { ok: false, message: dict.errorUnsupportedType };
  }
  if (response.status === 422) {
    // A backend-supplied message is free-form (not a stable, localizable
    // kind), so it's shown verbatim rather than mistranslated as if it were
    // frontend chrome.
    return { ok: false, message: extractMessage(body) ?? dict.errorProcessingFailed };
  }

  return { ok: false, message: dict.errorGeneric };
}
