import { afterEach, describe, expect, it, vi } from "vitest";

import { triggerAnalysis } from "@/lib/analysis-actions";

function validAnalysisBody() {
  return {
    id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    document_id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    document_type: "generic",
    extractor: "generic",
    status: "completed",
    summary: { title: null, purpose: "p", summary: "s", key_topics: [] },
    findings: [],
    important_dates: [],
    risks: [],
    specialized_analysis: null,
    provider: "openai",
    model: "gpt-4o-mini",
    created_at: "2026-08-29T12:34:56+00:00",
  };
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("triggerAnalysis", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the parsed analysis on 201", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(201, validAnalysisBody()))
    );

    const result = await triggerAnalysis("id");

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.analysis.provider).toBe("openai");
    }
  });

  it("posts to the same-origin route for exactly this document", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, validAnalysisBody()));
    vi.stubGlobal("fetch", fetchMock);

    await triggerAnalysis("5c68e652-ab9d-442d-a5b3-d24b015155ad");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/documents/5c68e652-ab9d-442d-a5b3-d24b015155ad/analysis",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("maps 404 to a not_found failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(404, { message: "Document not found." }))
    );

    const result = await triggerAnalysis("id");

    expect(result).toMatchObject({ ok: false, kind: "not_found" });
  });

  it("maps 409 to a conflict failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse(409, { message: "This document has no extracted text." })
        )
    );

    const result = await triggerAnalysis("id");

    expect(result).toMatchObject({ ok: false, kind: "conflict" });
  });

  it("maps 503 to a provider_unavailable failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(503, {})));

    const result = await triggerAnalysis("id");

    expect(result).toMatchObject({ ok: false, kind: "provider_unavailable" });
  });

  it("maps 502 to a distinct provider_invalid failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(502, {})));

    const result = await triggerAnalysis("id");

    expect(result).toMatchObject({ ok: false, kind: "provider_invalid" });
  });

  it("maps a network failure to unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));

    const result = await triggerAnalysis("id");

    expect(result).toMatchObject({ ok: false, kind: "unavailable" });
  });

  it("maps invalid JSON to malformed_response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("not json", { status: 201 }))
    );

    const result = await triggerAnalysis("id");

    expect(result).toMatchObject({ ok: false, kind: "malformed_response" });
  });

  it("maps a 201 with a schema-invalid payload to malformed_response and never renders it", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(201, { unexpected: true }))
    );

    const result = await triggerAnalysis("id");

    expect(result).toMatchObject({ ok: false, kind: "malformed_response" });
  });
});
