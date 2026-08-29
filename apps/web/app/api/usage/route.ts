import { NextResponse, type NextRequest } from "next/server";

import { anonymousHeader, anonymousSessionFor, applyAnonymousCookie } from "@/lib/anonymous-session";
import { BackendConfigError, getBackendBaseUrl } from "@/lib/backend-config";
import { usageResponseSchema } from "@/lib/usage-schema";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  let anonymousSession: ReturnType<typeof anonymousSessionFor>;
  try {
    anonymousSession = anonymousSessionFor(request);
  } catch {
    return NextResponse.json({ error: "server_configuration" }, { status: 502 });
  }

  let baseUrl: string;
  try {
    baseUrl = getBackendBaseUrl();
  } catch (error) {
    if (error instanceof BackendConfigError) {
      return NextResponse.json({ error: "server_configuration" }, { status: 502 });
    }
    throw error;
  }

  const documentId = request.nextUrl.searchParams.get("document_id");
  const query = documentId ? `?document_id=${encodeURIComponent(documentId)}` : "";
  let upstream: Response;
  try {
    upstream = await fetch(`${baseUrl}/api/usage${query}`, {
      headers: anonymousHeader(anonymousSession),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ error: "unavailable" }, { status: 502 });
  }
  if (!upstream.ok) return NextResponse.json({ error: "unavailable" }, { status: 502 });

  const parsed = usageResponseSchema.safeParse(await upstream.json());
  if (!parsed.success) return NextResponse.json({ error: "malformed_response" }, { status: 502 });
  return applyAnonymousCookie(NextResponse.json(parsed.data), anonymousSession);
}
