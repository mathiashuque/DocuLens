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

async function readBody(response: Response): Promise<unknown | undefined> {
  const text = await response.text();
  if (!text) return undefined;
  return JSON.parse(text) as unknown;
}

function failureFromResponse(response: Response, body: unknown): QuestionActionResult<never> {
  const error = body && typeof body === "object" && "error" in body
    ? (body as { error?: unknown }).error
    : undefined;
  const knownKinds: QuestionFailureKind[] = [
    "missing_index", "incompatible_index", "ineligible_document", "invalid_question",
    "not_found", "provider_unavailable", "provider_invalid", "server_configuration",
    "malformed_response", "unavailable",
  ];
  const kind = typeof error === "string" && knownKinds.includes(error as QuestionFailureKind)
    ? error as QuestionFailureKind
    : "unavailable";
  return {
    ok: false,
    kind,
    message: messageFrom(body) ?? (response.status === 422
      ? "Enter a valid question and try again."
      : "The Q&A service is currently unavailable. Try again shortly."),
  };
}

export async function prepareQuestionAnswering(documentId: string): Promise<QuestionActionResult<undefined>> {
  let response: Response;
  try {
    response = await fetch(`/api/documents/${encodeURIComponent(documentId)}/index`, { method: "POST" });
  } catch {
    return { ok: false, kind: "unavailable", message: "Could not reach the Q&A service. Try again." };
  }

  let body: unknown;
  try {
    body = await readBody(response);
  } catch {
    return { ok: false, kind: "malformed_response", message: "The Q&A service returned an unexpected response." };
  }
  if (response.status === 200 || response.status === 201) {
    return parseIndexResponseForDocument(documentId, body).success
      ? { ok: true, data: undefined }
      : { ok: false, kind: "malformed_response", message: "The Q&A service returned an unexpected response." };
  }
  return failureFromResponse(response, body);
}

export async function askDocumentQuestion(
  documentId: string,
  question: string,
): Promise<QuestionActionResult<QuestionResponse>> {
  const request = questionRequestSchema.safeParse({ question });
  if (!request.success) {
    return { ok: false, kind: "invalid_question", message: "Enter a question within the allowed length." };
  }

  let response: Response;
  try {
    response = await fetch(`/api/documents/${encodeURIComponent(documentId)}/questions`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(request.data),
    });
  } catch {
    return { ok: false, kind: "unavailable", message: "Could not reach the Q&A service. Try again." };
  }

  let body: unknown;
  try {
    body = await readBody(response);
  } catch {
    return { ok: false, kind: "malformed_response", message: "The Q&A service returned an unexpected response." };
  }
  if (response.ok) {
    const parsed = parseQuestionResponseForDocument(documentId, body);
    return parsed.success
      ? { ok: true, data: parsed.data }
      : { ok: false, kind: "malformed_response", message: "The Q&A service returned an unexpected response." };
  }
  return failureFromResponse(response, body);
}
