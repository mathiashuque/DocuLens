import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AnalyzeButton } from "@/components/analysis/AnalyzeButton";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

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

describe("AnalyzeButton", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows idle, then submitting, then calls onSuccess with the validated analysis", async () => {
    let resolveFetch: (value: Response) => void = () => {};
    const fetchMock = vi.fn().mockReturnValue(
      new Promise<Response>((resolve) => {
        resolveFetch = resolve;
      })
    );
    vi.stubGlobal("fetch", fetchMock);
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    render(<AnalyzeButton documentId="doc-1" onSuccess={onSuccess} />);

    const button = screen.getByRole("button", { name: "Analyze document" });
    await user.click(button);

    expect(screen.getByRole("button", { name: "Analyzing…" })).toBeDisabled();

    resolveFetch(jsonResponse(201, validAnalysisBody()));

    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
    expect(onSuccess.mock.calls[0][0].provider).toBe("openai");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("prevents a double submission from issuing two requests", async () => {
    let resolveFetch: (value: Response) => void = () => {};
    const fetchMock = vi.fn().mockReturnValue(
      new Promise<Response>((resolve) => {
        resolveFetch = resolve;
      })
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<AnalyzeButton documentId="doc-1" onSuccess={vi.fn()} />);

    const button = screen.getByRole("button", { name: "Analyze document" });
    await user.click(button);
    await user.click(screen.getByRole("button", { name: "Analyzing…" }));

    resolveFetch(jsonResponse(201, validAnalysisBody()));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  });

  it("shows a distinct message for a conflict (textless document) failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(409, { message: "This document has no extracted text." })
      )
    );
    const user = userEvent.setup();
    render(<AnalyzeButton documentId="doc-1" onSuccess={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Analyze document" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("no extracted text");
    });
    expect(screen.getByRole("button", { name: "Analyze document" })).toBeEnabled();
  });

  it("shows a distinct message for an unavailable provider (503)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(503, {})));
    const user = userEvent.setup();
    render(<AnalyzeButton documentId="doc-1" onSuccess={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Analyze document" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("unavailable");
    });
  });

  it("shows a distinct message for invalid provider output (502)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(502, {})));
    const user = userEvent.setup();
    render(<AnalyzeButton documentId="doc-1" onSuccess={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Analyze document" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("failed to produce");
    });
  });

  it("fails closed and never calls onSuccess on a malformed response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("not json", { status: 201 }))
    );
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    render(<AnalyzeButton documentId="doc-1" onSuccess={onSuccess} />);

    await user.click(screen.getByRole("button", { name: "Analyze document" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it("allows a deliberate manual retry after a failure", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(503, {}))
      .mockResolvedValueOnce(jsonResponse(201, validAnalysisBody()));
    vi.stubGlobal("fetch", fetchMock);
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    render(<AnalyzeButton documentId="doc-1" onSuccess={onSuccess} />);

    await user.click(screen.getByRole("button", { name: "Analyze document" }));
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Analyze document" }));

    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("never automatically retries on its own", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(503, {}));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<AnalyzeButton documentId="doc-1" onSuccess={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Analyze document" }));
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());

    // Give any hypothetical auto-retry timer a chance to fire.
    await new Promise((resolve) => setTimeout(resolve, 50));

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
