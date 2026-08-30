import type { Dictionary } from "./i18n/dictionary";
import { interpolate } from "./i18n/interpolate";
import { FORMATTING_LOCALE, type Locale } from "./i18n/locales";
import {
  parseIndexResponseForDocument,
  parseQuestionResponseForDocument,
  questionRequestSchema,
  type QuestionResponse,
} from "./question-schema";

export type QuestionFailureKind =
  | "missing_index"
  | "incompatible_index"
  | "ineligible_document"
  | "invalid_question"
  | "not_found"
  | "provider_unavailable"
  | "provider_invalid"
  | "server_configuration"
  | "malformed_response"
  | "quota_exceeded"
  | "unavailable";

export type QuestionActionResult<T> =
  | { ok: true; data: T }
  | { ok: false; kind: QuestionFailureKind; message: string };

function messageFrom(body: unknown): string | undefined {
  if (body && typeof body === "object" && "message" in body) {
    const message = (body as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) return message;
  }
  return undefined;
}

function messageWithReset(body: unknown, dict: Dictionary["errors"], locale: Locale): string | undefined {
  const message = messageFrom(body);
  if (!message || !body || typeof body !== "object" || !("retry_at" in body)) return message;
  const retryAt = (body as { retry_at?: unknown }).retry_at;
  if (typeof retryAt !== "string") return message;
  const reset = new Date(retryAt);
  if (Number.isNaN(reset.getTime())) return message;
  const time = new Intl.DateTimeFormat(FORMATTING_LOCALE[locale], { dateStyle: "medium", timeStyle: "short" }).format(
    reset
  );
  return `${message}${interpolate(dict.resetSuffix, { time })}`;
}

async function readBody(response: Response): Promise<unknown | undefined> {
  const text = await response.text();
  if (!text) return undefined;
  return JSON.parse(text) as unknown;
}

function failureFromResponse(
  response: Response,
  body: unknown,
  dict: Dictionary["errors"],
  locale: Locale
): QuestionActionResult<never> {
  const error = body && typeof body === "object" && "error" in body
    ? (body as { error?: unknown }).error
    : undefined;
  const knownKinds: QuestionFailureKind[] = [
    "missing_index", "incompatible_index", "ineligible_document", "invalid_question",
    "not_found", "provider_unavailable", "provider_invalid", "server_configuration",
    "malformed_response", "quota_exceeded", "unavailable",
  ];
  const kind = typeof error === "string" && knownKinds.includes(error as QuestionFailureKind)
    ? error as QuestionFailureKind
    : "unavailable";
  return {
    ok: false,
    kind,
    message:
      messageWithReset(body, dict, locale) ??
      (response.status === 422 ? dict.validQuestionRetry : dict.qaUnavailable),
  };
}

export async function prepareQuestionAnswering(
  documentId: string,
  dict: Dictionary["errors"],
  locale: Locale
): Promise<QuestionActionResult<undefined>> {
  let response: Response;
  try {
    response = await fetch(`/api/documents/${encodeURIComponent(documentId)}/index`, { method: "POST" });
  } catch {
    return { ok: false, kind: "unavailable", message: dict.networkUnavailable };
  }

  let body: unknown;
  try {
    body = await readBody(response);
  } catch {
    return { ok: false, kind: "malformed_response", message: dict.malformedResponse };
  }
  if (response.status === 200 || response.status === 201) {
    return parseIndexResponseForDocument(documentId, body).success
      ? { ok: true, data: undefined }
      : { ok: false, kind: "malformed_response", message: dict.malformedResponse };
  }
  return failureFromResponse(response, body, dict, locale);
}

export async function askDocumentQuestion(
  documentId: string,
  question: string,
  dict: Dictionary["errors"],
  locale: Locale
): Promise<QuestionActionResult<QuestionResponse>> {
  const request = questionRequestSchema.safeParse({ question });
  if (!request.success) {
    return { ok: false, kind: "invalid_question", message: dict.invalidQuestion };
  }

  let response: Response;
  try {
    response = await fetch(`/api/documents/${encodeURIComponent(documentId)}/questions`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request.data),
    });
  } catch {
    return { ok: false, kind: "unavailable", message: dict.networkUnavailable };
  }

  let body: unknown;
  try {
    body = await readBody(response);
  } catch {
    return { ok: false, kind: "malformed_response", message: dict.malformedResponse };
  }
  if (response.ok) {
    const parsed = parseQuestionResponseForDocument(documentId, body);
    return parsed.success
      ? { ok: true, data: parsed.data }
      : { ok: false, kind: "malformed_response", message: dict.malformedResponse };
  }
  return failureFromResponse(response, body, dict, locale);
}
