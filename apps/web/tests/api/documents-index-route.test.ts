// @vitest-environment node
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
import { POST } from "@/app/api/documents/[documentId]/index/route";

const DOCUMENT_ID = "5c68e652-ab9d-442d-a5b3-d24b015155ad";
const response = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
const call = (fetchMock: ReturnType<typeof vi.fn>) => {
  vi.stubGlobal("fetch", fetchMock);
  return POST(new NextRequest(`http://localhost/api/documents/${DOCUMENT_ID}/index`, { method: "POST" }), { params: Promise.resolve({ documentId: DOCUMENT_ID }) });
};

describe("index proxy", () => {
  beforeEach(() => vi.stubEnv("DOCULENS_API_BASE_URL", "http://api.test"));
  afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });
  it.each([200, 201])("accepts valid idempotent index success (%i)", async (status) => {
    const result = await call(vi.fn().mockResolvedValue(response(status, { document_id: DOCUMENT_ID, status: "completed", chunk_count: 2 })));
    expect(result.status).toBe(status);
    expect(await result.json()).toEqual({ document_id: DOCUMENT_ID, status: "completed" });
  });
  it("normalizes recognized failures and malformed upstream success safely", async () => {
    const ineligible = await call(vi.fn().mockResolvedValue(response(409, { detail: "Document is not eligible for indexing." })));
    expect((await ineligible.json()).error).toBe("ineligible_document");
    const malformed = await call(vi.fn().mockResolvedValue(response(201, { document_id: "not-a-uuid", status: "completed" })));
    expect((await malformed.json()).error).toBe("malformed_response");
  });
});
