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
 * failure could create a duplicate persisted document.
 */
export async function uploadDocument(
  file: File,
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
    return {
      ok: false,
      message:
        "Could not reach the upload service. Check your connection and try again.",
    };
  }

  const text = await response.text();
  let body: unknown;
  try {
    body = text ? JSON.parse(text) : undefined;
  } catch {
    return {
      ok: false,
      message: "The upload service returned an unexpected response.",
    };
  }

  if (response.status === 201) {
    const result = parseDocument(body);
    if (!result.success) {
      return {
        ok: false,
        message: "The upload service returned an unexpected response.",
      };
    }
    return { ok: true, document: result.data };
  }

  if (response.status === 413) {
    return { ok: false, message: "That file is too large. Upload a PDF under 10 MB." };
  }
  if (response.status === 415) {
    return { ok: false, message: "That file type isn't supported. Upload a PDF." };
  }
  if (response.status === 422) {
    return {
      ok: false,
      message:
        extractMessage(body) ??
        "The PDF could not be processed. It may be encrypted or corrupted.",
    };
  }

  return {
    ok: false,
    message: "Something went wrong uploading the document. Please try again.",
  };
}
