// @vitest-environment node
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
import { POST } from "@/app/api/documents/[documentId]/questions/route";

const DOCUMENT_ID = "5c68e652-ab9d-442d-a5b3-d24b015155ad";
const upstream = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
function request(body: unknown) { return new NextRequest(`http://localhost/api/documents/${DOCUMENT_ID}/questions`, { method: "POST", body: JSON.stringify(body), headers: { "content-type": "application/json" } }); }

describe("questions proxy", () => {
  beforeEach(() => vi.stubEnv("DOCULENS_API_BASE_URL", "http://api.test"));
  afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });
  it("forwards only the validated question and returns an answered response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(upstream(200, { document_id: DOCUMENT_ID, question: "What applies?", status: "answered", answer: "This applies.", citations: [{ chunk_id: "1a5501f3-425d-4d34-b7e2-7db61e37351e", page: 1, evidence: "Evidence." }] }));
    vi.stubGlobal("fetch", fetchMock);
    const result = await POST(request({ question: "What applies?" }), { params: Promise.resolve({ documentId: DOCUMENT_ID }) });
    expect(result.status).toBe(200);
    expect((fetchMock.mock.calls[0][1] as RequestInit).body).toBe(JSON.stringify({ question: "What applies?" }));
  });
  it("rejects invalid bodies and maps a missing index without exposing detail", async () => {
    const invalid = await POST(request({ question: " ", top_k: 1 }), { params: Promise.resolve({ documentId: DOCUMENT_ID }) });
    expect((await invalid.json()).error).toBe("invalid_question");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(upstream(404, { detail: "No completed index exists." })));
    const missing = await POST(request({ question: "What applies?" }), { params: Promise.resolve({ documentId: DOCUMENT_ID }) });
    expect((await missing.json()).error).toBe("missing_index");
  });
});
