import { NextResponse, type NextRequest } from "next/server";

import { getBackendBaseUrl, BackendConfigError } from "@/lib/backend-config";
import { parseQuestionResponseForDocument, questionRequestSchema } from "@/lib/question-schema";
import { anonymousHeader, anonymousSessionFor, applyAnonymousCookie } from "@/lib/anonymous-session";

export const runtime = "nodejs";
const REQUEST_TIMEOUT_MS = 60_000;
type RouteContext = { params: Promise<{ documentId: string }> };

function safeError(status: number, error: string, message: string) { return NextResponse.json({ error, message }, { status }); }
function detail(body: unknown): string | undefined {
  if (body && typeof body === "object" && "detail" in body) {
    const value = (body as { detail?: unknown }).detail;
    return typeof value === "string" && value.trim() ? value : undefined;
  }
  return undefined;
}

export async function POST(request: NextRequest, { params }: RouteContext) {
  const { documentId } = await params;
  let input: unknown;
  try { input = await request.json(); } catch { return safeError(422, "invalid_question", "Enter a valid question and try again."); }
  const parsedInput = questionRequestSchema.safeParse(input);
  if (!parsedInput.success) return safeError(422, "invalid_question", "Enter a valid question and try again.");
  let anonymousSession: ReturnType<typeof anonymousSessionFor>;
  try { anonymousSession = anonymousSessionFor(request); } catch { return safeError(502, "server_configuration", "Usage protection is not configured."); }
  let baseUrl: string;
  try { baseUrl = getBackendBaseUrl(); } catch (error) {
    if (error instanceof BackendConfigError) return safeError(502, "server_configuration", "The Q&A service is not configured.");
    throw error;
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/documents/${encodeURIComponent(documentId)}/questions`, {
      method: "POST", headers: { "content-type": "application/json", ...anonymousHeader(anonymousSession) }, body: JSON.stringify(parsedInput.data), signal: controller.signal,
    });
  } catch { return safeError(502, "unavailable", "The Q&A service is currently unavailable."); } finally { clearTimeout(timeout); }
  let body: unknown;
  try { body = await response.json(); } catch { return safeError(502, "malformed_response", "The Q&A service returned an unexpected response."); }
  if (response.ok) {
    const result = parseQuestionResponseForDocument(documentId, body);
    return result.success ? applyAnonymousCookie(NextResponse.json(result.data), anonymousSession) : safeError(502, "malformed_response", "The Q&A service returned an unexpected response.");
  }
  if (response.status === 429) {
    return applyAnonymousCookie(NextResponse.json({ error: "quota_exceeded", message: "This document’s anonymous question allowance is exhausted. Precomputed demos remain available.", retry_at: null }, { status: 429 }), anonymousSession);
  }
  const upstreamDetail = detail(body);
  if (response.status === 404) {
    if (upstreamDetail === "No completed index exists.") return safeError(409, "missing_index", "Prepare Q&A before asking a question.");
    if (upstreamDetail === "Document not found.") return safeError(404, "not_found", "Document not found.");
  }
  if (response.status === 409 && upstreamDetail === "The stored index is incompatible with the current embedding configuration.") return safeError(409, "incompatible_index", "This document’s existing Q&A index is incompatible. Please contact the operator.");
  if (response.status === 422) return safeError(422, "invalid_question", "Enter a valid question and try again.");
  if (response.status === 503) return safeError(503, "provider_unavailable", "The generation service is currently unavailable.");
  if (response.status === 502) return safeError(502, "provider_invalid", "The generation service failed to produce a valid result.");
  return safeError(502, "unavailable", "The Q&A service returned an unexpected error.");
}
