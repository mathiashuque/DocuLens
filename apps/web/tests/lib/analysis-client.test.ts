import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { fetchAnalysis, loadAnalysis } from "@/lib/analysis-client";
import { BackendError } from "@/lib/errors";

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

describe("fetchAnalysis", () => {
  beforeEach(() => {
    vi.stubEnv("DOCULENS_API_BASE_URL", "http://localhost:8000");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("returns the parsed analysis on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(200, validAnalysisBody()))
    );

    const analysis = await fetchAnalysis("5c68e652-ab9d-442d-a5b3-d24b015155ad");

    expect(analysis?.provider).toBe("openai");
  });

  it("returns null when no completed analysis exists (404)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(404, { detail: "No completed analysis." }))
    );

    const analysis = await fetchAnalysis("id");

    expect(analysis).toBeNull();
  });

  it("throws unavailable without leaking the response body on a 500", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(500, { secret: "internal stack trace" }))
    );

    const error = await fetchAnalysis("id").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(BackendError);
    expect((error as BackendError).kind).toBe("unavailable");
    expect((error as BackendError).message).not.toMatch(/secret|stack trace/);
  });

  it("throws unavailable when the network request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));

    await expect(fetchAnalysis("id")).rejects.toMatchObject({ kind: "unavailable" });
  });

  it("throws malformed_response on invalid JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("not json", { status: 200 }))
    );

    await expect(fetchAnalysis("id")).rejects.toMatchObject({
      kind: "malformed_response",
    });
  });

  it("throws malformed_response when the payload fails schema validation", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(200, { unexpected: true }))
    );

    await expect(fetchAnalysis("id")).rejects.toMatchObject({
      kind: "malformed_response",
    });
  });

  it("never leaks the configured backend base URL in a thrown message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));

    const error = await fetchAnalysis("id").catch((caught: unknown) => caught);

    expect((error as BackendError).message).not.toMatch(/localhost:8000/);
  });
});

describe("loadAnalysis", () => {
  beforeEach(() => {
    vi.stubEnv("DOCULENS_API_BASE_URL", "http://localhost:8000");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("returns a ready result on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(200, validAnalysisBody()))
    );

    const result = await loadAnalysis("id");

    expect(result.status).toBe("ready");
  });

  it("returns a none result when no completed analysis exists", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(404, {})));

    const result = await loadAnalysis("id");

    expect(result).toEqual({ status: "none" });
  });

  it("never throws: returns an error result instead", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));

    const result = await loadAnalysis("id");

    expect(result.status).toBe("error");
  });
});
