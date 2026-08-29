import { afterEach, describe, expect, it, vi } from "vitest";

import { uploadDocument } from "@/lib/upload";

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

const file = new File(["%PDF-1.4"], "doc.pdf", { type: "application/pdf" });

describe("uploadDocument", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the parsed document on success", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, validDocumentBody()));
    vi.stubGlobal("fetch", fetchMock);

    const result = await uploadDocument(file);

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.document.id).toBe("5c68e652-ab9d-442d-a5b3-d24b015155ad");
    }
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/documents",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("fails safely when the success body does not match the contract", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, { unexpected: true }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await uploadDocument(file);

    expect(result.ok).toBe(false);
  });

  it("maps 413 to a friendly size message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(413, { message: "too big" }))
    );

    const result = await uploadDocument(file);

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.message).toMatch(/10 MB/);
    }
  });

  it("maps 415 to a friendly type message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(415, {})));

    const result = await uploadDocument(file);

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.message).toMatch(/PDF/);
    }
  });

  it("surfaces the safe backend message for 422", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(422, { message: "Encrypted PDFs are not supported." }))
    );

    const result = await uploadDocument(file);

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.message).toBe("Encrypted PDFs are not supported.");
    }
  });

  it("returns a generic message for an unexpected status", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(500, {})));

    const result = await uploadDocument(file);

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.message).not.toMatch(/<|>/);
    }
  });

  it("handles a network failure without throwing", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));

    const result = await uploadDocument(file);

    expect(result.ok).toBe(false);
  });

  it("handles a malformed JSON response safely", async () => {
    const malformed = new Response("not json", { status: 201 });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(malformed));

    const result = await uploadDocument(file);

    expect(result.ok).toBe(false);
  });

  it("makes exactly one request per call and never retries automatically", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(500, {}));
    vi.stubGlobal("fetch", fetchMock);

    await uploadDocument(file);

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
