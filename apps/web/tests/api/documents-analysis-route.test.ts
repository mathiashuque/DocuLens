// @vitest-environment node
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { POST } from "@/app/api/documents/[documentId]/analysis/route";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function analysisRequest(documentId: string): NextRequest {
  return new NextRequest(
    `http://localhost:3000/api/documents/${documentId}/analysis`,
    { method: "POST" }
  );
}

const DOCUMENT_ID = "5c68e652-ab9d-442d-a5b3-d24b015155ad";

function callPost(fetchMock: ReturnType<typeof vi.fn>) {
  vi.stubGlobal("fetch", fetchMock);
  return POST(analysisRequest(DOCUMENT_ID), {
    params: Promise.resolve({ documentId: DOCUMENT_ID }),
  });
}

describe("POST /api/documents/[documentId]/analysis", () => {
  beforeEach(() => {
    vi.stubEnv("DOCULENS_API_BASE_URL", "http://localhost:8000");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("forwards to the exact backend document ID and returns the 201 body", async () => {
    const analysisBody = { id: "analysis-1", document_id: DOCUMENT_ID };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, analysisBody));

    const response = await callPost(fetchMock);

    expect(response.status).toBe(201);
    expect(await response.json()).toEqual(analysisBody);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(`http://localhost:8000/api/documents/${DOCUMENT_ID}/analysis`);
    expect(init.method).toBe("POST");
  });

  it("passes through a 404 as not_found", async () => {
    const response = await callPost(
      vi.fn().mockResolvedValue(jsonResponse(404, { detail: "Document not found." }))
    );

    expect(response.status).toBe(404);
    const body = await response.json();
    expect(body.error).toBe("not_found");
  });

  it("passes through a 409 with the backend's safe detail as a conflict", async () => {
    const response = await callPost(
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse(409, { detail: "Document has no extracted text available to analyze." })
        )
    );

    expect(response.status).toBe(409);
    const body = await response.json();
    expect(body.error).toBe("textless_document");
    expect(body.message).toBe("Document has no extracted text available to analyze.");
  });

  it("maps a 503 to a distinct provider_unavailable error", async () => {
    const response = await callPost(vi.fn().mockResolvedValue(jsonResponse(503, {})));

    expect(response.status).toBe(503);
    const body = await response.json();
    expect(body.error).toBe("provider_unavailable");
  });

  it("maps a 502 to a distinct provider_invalid error", async () => {
    const response = await callPost(vi.fn().mockResolvedValue(jsonResponse(502, {})));

    expect(response.status).toBe(502);
    const body = await response.json();
    expect(body.error).toBe("provider_invalid");
  });

  it("returns a safe 502 when the backend is unreachable, without leaking the network error", async () => {
    const response = await callPost(
      vi.fn().mockRejectedValue(new TypeError("connection refused"))
    );

    expect(response.status).toBe(502);
    const body = await response.json();
    expect(JSON.stringify(body)).not.toMatch(/connection refused/);
  });

  it("returns a safe 502 when the upstream response is not JSON", async () => {
    const response = await callPost(
      vi.fn().mockResolvedValue(new Response("<html>bad gateway</html>", { status: 201 }))
    );

    expect(response.status).toBe(502);
  });

  it("returns a safe 502 for an unexpected upstream status without leaking its body", async () => {
    const response = await callPost(
      vi.fn().mockResolvedValue(jsonResponse(500, { detail: "internal stack trace" }))
    );

    expect(response.status).toBe(502);
    const body = await response.json();
    expect(JSON.stringify(body)).not.toMatch(/internal stack trace/);
  });

  it("never sends a request body to the upstream analysis endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, {}));

    await callPost(fetchMock);

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.body).toBeUndefined();
  });
});
