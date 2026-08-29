import { NextResponse, type NextRequest } from "next/server";

import { getBackendBaseUrl, BackendConfigError } from "@/lib/backend-config";
import { parseIndexResponseForDocument } from "@/lib/question-schema";
import { anonymousHeader, anonymousSessionFor, applyAnonymousCookie } from "@/lib/anonymous-session";

export const runtime = "nodejs";
const REQUEST_TIMEOUT_MS = 60_000;
type RouteContext = { params: Promise<{ documentId: string }> };

function safeError(status: number, error: string, message: string) {
  return NextResponse.json({ error, message }, { status });
}

function detail(body: unknown): string | undefined {
  if (body && typeof body === "object" && "detail" in body) {
    const value = (body as { detail?: unknown }).detail;
    return typeof value === "string" && value.trim() ? value : undefined;
  }
  return undefined;
}

export async function POST(request: NextRequest, { params }: RouteContext) {
  const { documentId } = await params;
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
    response = await fetch(`${baseUrl}/api/documents/${encodeURIComponent(documentId)}/index`, { method: "POST", headers: anonymousHeader(anonymousSession), signal: controller.signal });
  } catch {
    return safeError(502, "unavailable", "The Q&A service is currently unavailable.");
  } finally { clearTimeout(timeout); }
  let body: unknown;
  try { body = await response.json(); } catch { return safeError(502, "malformed_response", "The Q&A service returned an unexpected response."); }
  if (response.status === 200 || response.status === 201) {
    const parsed = parseIndexResponseForDocument(documentId, body);
    return parsed.success
      ? applyAnonymousCookie(NextResponse.json(parsed.data, { status: response.status }), anonymousSession)
      : safeError(502, "malformed_response", "The Q&A service returned an unexpected response.");
  }
  if (response.status === 429) {
    const retryAt = body && typeof body === "object" && "retry_at" in body ? (body as { retry_at?: unknown }).retry_at : null;
    return applyAnonymousCookie(NextResponse.json({ error: "quota_exceeded", message: "Your daily Q&A preparation allowance is exhausted. Precomputed demos remain available.", retry_at: typeof retryAt === "string" ? retryAt : null }, { status: 429 }), anonymousSession);
  }
  if (response.status === 404 && detail(body) === "Document not found.") return safeError(404, "not_found", "Document not found.");
  if (response.status === 409) {
    if (detail(body) === "Document is not eligible for indexing.") return safeError(409, "ineligible_document", "This document is not eligible for Q&A.");
    if (detail(body) === "An existing index is incompatible with the current embedding configuration.") return safeError(409, "incompatible_index", "This document’s existing Q&A index is incompatible. Please contact the operator.");
  }
  if (response.status === 503) return safeError(503, "provider_unavailable", "The embedding service is currently unavailable.");
  if (response.status === 502) return safeError(502, "provider_invalid", "The embedding service failed to produce a valid result.");
  return safeError(502, "unavailable", "The Q&A service returned an unexpected error.");
}
