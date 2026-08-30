// @vitest-environment node
//
// Runs under Node rather than jsdom: NextRequest's formData()/File objects
// come from Node/undici, not jsdom's File, so `instanceof File` checks in
// the route handler must be tested against the same realm it runs in.
import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { POST } from "@/app/api/documents/route";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function requestWithFile(fields: Record<string, File | string>): NextRequest {
  const form = new FormData();
  for (const [key, value] of Object.entries(fields)) {
    form.set(key, value);
  }
  return new NextRequest("http://localhost:3000/api/documents", {
    method: "POST",
    body: form,
  });
}

const pdfFile = new File(["%PDF-1.4"], "doc.pdf", { type: "application/pdf" });

describe("POST /api/documents", () => {
  beforeEach(() => {
    vi.stubEnv("DOCULENS_API_BASE_URL", "http://localhost:8000");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("forwards the file and returns the backend's 201 document body", async () => {
    const documentBody = { id: "abc", filename: "doc.pdf" };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, documentBody));
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(requestWithFile({ file: pdfFile }));

    expect(response.status).toBe(201);
    expect(await response.json()).toEqual(documentBody);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/documents");
    const forwardedForm = init.body as FormData;
    expect(Array.from(forwardedForm.keys())).toEqual(["file"]);
  });

  it("does not forward arbitrary extra fields from the incoming form", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, {}));
    vi.stubGlobal("fetch", fetchMock);

    await POST(requestWithFile({ file: pdfFile, extra: "should-not-forward" }));

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const forwardedForm = init.body as FormData;
    expect(Array.from(forwardedForm.keys())).toEqual(["file"]);
  });

  it("returns 400 when no file field is present", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(requestWithFile({}));

    expect(response.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("passes through a 422 with the backend's safe detail message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(422, { detail: "Encrypted PDFs are not supported." }))
    );

    const response = await POST(requestWithFile({ file: pdfFile }));

    expect(response.status).toBe(422);
    const body = await response.json();
    expect(body.message).toBe("Encrypted PDFs are not supported.");
  });

  it("returns a safe 502 when the backend is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("connection refused")));

    const response = await POST(requestWithFile({ file: pdfFile }));

    expect(response.status).toBe(502);
    const body = await response.json();
    expect(JSON.stringify(body)).not.toMatch(/connection refused/);
  });

  it("returns a safe 502 when the upstream response is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("<html>bad gateway</html>", { status: 201 }))
    );

    const response = await POST(requestWithFile({ file: pdfFile }));

    expect(response.status).toBe(502);
  });

  it("returns a safe 502 for an unexpected upstream status", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(500, { detail: "boom" })));

    const response = await POST(requestWithFile({ file: pdfFile }));

    expect(response.status).toBe(502);
    const body = await response.json();
    expect(body.message).not.toMatch(/boom/);
  });
});
