import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { fetchDocument } from "@/lib/backend-client";
import { BackendError } from "@/lib/errors";

function validDocumentBody() {
  return {
    id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    filename: "contract.pdf",
    content_hash: "a".repeat(64),
    status: "parsed",
    page_count: 1,
    created_at: "2026-08-29T12:34:56+00:00",
    pages: [{ page_number: 1, text: "hello" }],
    sections: [],
  };
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("fetchDocument", () => {
  beforeEach(() => {
    vi.stubEnv("DOCULENS_API_BASE_URL", "http://localhost:8000");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("returns the parsed document on success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, validDocumentBody())));

    const document = await fetchDocument("5c68e652-ab9d-442d-a5b3-d24b015155ad");

    expect(document.filename).toBe("contract.pdf");
  });

  it("throws a not_found BackendError on 404", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(404, { detail: "Document not found." })));

    await expect(fetchDocument("missing")).rejects.toMatchObject({
      kind: "not_found",
    } satisfies Partial<BackendError>);
  });

  it("throws a not_found BackendError on a malformed-ID 422", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(422, {})));

    await expect(fetchDocument("not-a-uuid")).rejects.toMatchObject({
      kind: "not_found",
    });
  });

  it("throws unavailable without leaking the response body on a 500", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(500, { secret: "internal stack trace" }))
    );

    const error = await fetchDocument("id").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(BackendError);
    expect((error as BackendError).kind).toBe("unavailable");
    expect((error as BackendError).message).not.toMatch(/secret|stack trace/);
  });

  it("throws unavailable when the network request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));

    await expect(fetchDocument("id")).rejects.toMatchObject({ kind: "unavailable" });
  });

  it("throws malformed_response on invalid JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not json", { status: 200 })));

    await expect(fetchDocument("id")).rejects.toMatchObject({
      kind: "malformed_response",
    });
  });

  it("throws malformed_response when the payload fails schema validation", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, { unexpected: true })));

    await expect(fetchDocument("id")).rejects.toMatchObject({
      kind: "malformed_response",
    });
  });

  it("never leaks the configured backend base URL in a thrown message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));

    const error = await fetchDocument("id").catch((caught: unknown) => caught);

    expect((error as BackendError).message).not.toMatch(/localhost:8000/);
  });
});
