import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AnalysisPanel } from "@/components/analysis/AnalysisPanel";
import type { AnalysisLoadResult } from "@/lib/analysis-client";
import type { Analysis } from "@/lib/analysis-schema";

function validAnalysis(overrides: Partial<Analysis> = {}): Analysis {
  return {
    id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    document_id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    document_type: "generic",
    extractor: "generic",
    status: "completed",
    summary: {
      title: null,
      purpose: "Explains the document.",
      summary: "A summary.",
      key_topics: [],
    },
    findings: [],
    important_dates: [],
    risks: [],
    specialized_analysis: null,
    provider: "openai",
    model: "gpt-4o-mini",
    created_at: "2026-08-29T12:34:56+00:00",
    ...overrides,
  };
}

describe("AnalysisPanel", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows the analyze action when no analysis exists yet", () => {
    render(
      <AnalysisPanel
        documentId="doc-1"
        documentStatus="parsed"
        documentPageNumbers={[1]}
        initialLoad={{ status: "none" } satisfies AnalysisLoadResult}
      />
    );

    expect(screen.getByRole("button", { name: "Analyze document" })).toBeInTheDocument();
  });

  it("renders a completed analysis without ever calling a provider-triggering endpoint", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(
      <AnalysisPanel
        documentId="doc-1"
        documentStatus="parsed"
        documentPageNumbers={[1]}
        initialLoad={
          { status: "ready", analysis: validAnalysis() } satisfies AnalysisLoadResult
        }
      />
    );

    expect(screen.getByText("Explains the document.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("never offers analysis for an OCR-required document", () => {
    const { container } = render(
      <AnalysisPanel
        documentId="doc-1"
        documentStatus="ocr_required"
        documentPageNumbers={[]}
        initialLoad={{ status: "none" } satisfies AnalysisLoadResult}
      />
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("shows a localized error and still offers the analyze action when the load failed", () => {
    render(
      <AnalysisPanel
        documentId="doc-1"
        documentStatus="parsed"
        documentPageNumbers={[1]}
        initialLoad={
          {
            status: "error",
            message: "The analysis service returned an unexpected error.",
          } satisfies AnalysisLoadResult
        }
      />
    );

    expect(screen.getByRole("alert")).toHaveTextContent("unexpected error");
    expect(screen.getByRole("button", { name: "Analyze document" })).toBeInTheDocument();
  });

  it("fails closed with a safe error when the analysis cites a page absent from the document", () => {
    render(
      <AnalysisPanel
        documentId="doc-1"
        documentStatus="parsed"
        documentPageNumbers={[1, 2]}
        initialLoad={
          {
            status: "ready",
            analysis: validAnalysis({
              findings: [
                {
                  id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
                  title: "t",
                  description: "d",
                  category: "c",
                  importance: "low",
                  source_page: 99,
                  evidence: "e",
                  confidence: 0.5,
                },
              ],
            }),
          } satisfies AnalysisLoadResult
        }
      />
    );

    expect(screen.getByRole("alert")).toHaveTextContent("can’t be shown safely");
    expect(screen.queryByText("t")).not.toBeInTheDocument();
  });
});
