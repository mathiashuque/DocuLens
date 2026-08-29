import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

const { fetchDocumentMock, loadAnalysisMock, notFoundMock, NotFoundSignal } = vi.hoisted(
  () => {
    class HoistedNotFoundSignal extends Error {}
    return {
      fetchDocumentMock: vi.fn(),
      loadAnalysisMock: vi.fn(),
      notFoundMock: vi.fn(() => {
        throw new HoistedNotFoundSignal("NEXT_NOT_FOUND");
      }),
      NotFoundSignal: HoistedNotFoundSignal,
    };
  }
);

vi.mock("@/lib/backend-client", () => ({
  fetchDocument: fetchDocumentMock,
}));

vi.mock("@/lib/analysis-client", () => ({
  loadAnalysis: loadAnalysisMock,
}));

vi.mock("next/navigation", () => ({
  notFound: notFoundMock,
}));

import DocumentPage from "@/app/documents/[documentId]/page";
import { BackendError } from "@/lib/errors";

function validDocument(overrides: Record<string, unknown> = {}) {
  return {
    id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    filename: "contract.pdf",
    content_hash: "a".repeat(64),
    status: "parsed" as const,
    page_count: 1,
    created_at: "2026-08-29T12:34:56+00:00",
    pages: [{ page_number: 1, text: "hello" }],
    sections: [],
    ...overrides,
  };
}

function validAnalysis() {
  return {
    id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    document_id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    document_type: "generic" as const,
    extractor: "generic" as const,
    status: "completed" as const,
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
  };
}

describe("DocumentPage", () => {
  beforeEach(() => {
    loadAnalysisMock.mockReset();
    loadAnalysisMock.mockResolvedValue({ status: "none" });
  });

  it("renders the persisted document's summary, sections, and pages", async () => {
    fetchDocumentMock.mockResolvedValueOnce(validDocument());

    const jsx = await DocumentPage({
      params: Promise.resolve({ documentId: "5c68e652-ab9d-442d-a5b3-d24b015155ad" }),
    });
    render(jsx);

    expect(screen.getByRole("heading", { name: "contract.pdf" })).toBeInTheDocument();
    expect(screen.getByText("Page 1")).toBeInTheDocument();
    expect(screen.getByText(/No reliable headings were detected/)).toBeInTheDocument();
  });

  it("calls notFound() when the backend reports the document is missing", async () => {
    fetchDocumentMock.mockRejectedValueOnce(
      new BackendError("not_found", "Document not found.", 404)
    );

    await expect(
      DocumentPage({ params: Promise.resolve({ documentId: "missing" }) })
    ).rejects.toBeInstanceOf(NotFoundSignal);
    expect(notFoundMock).toHaveBeenCalled();
  });

  it("re-throws unexpected backend errors for the error boundary", async () => {
    fetchDocumentMock.mockRejectedValueOnce(
      new BackendError("unavailable", "The document service is currently unavailable.")
    );

    await expect(
      DocumentPage({ params: Promise.resolve({ documentId: "id" }) })
    ).rejects.toBeInstanceOf(BackendError);
  });

  it("shows the analyze action when a parsed document has no completed analysis", async () => {
    fetchDocumentMock.mockResolvedValueOnce(validDocument());
    loadAnalysisMock.mockResolvedValueOnce({ status: "none" });

    const jsx = await DocumentPage({
      params: Promise.resolve({ documentId: "5c68e652-ab9d-442d-a5b3-d24b015155ad" }),
    });
    render(jsx);

    expect(screen.getByRole("button", { name: "Analyze document" })).toBeInTheDocument();
  });

  it("renders a completed analysis loaded via GET", async () => {
    fetchDocumentMock.mockResolvedValueOnce(validDocument());
    loadAnalysisMock.mockResolvedValueOnce({
      status: "ready",
      analysis: validAnalysis(),
    });

    const jsx = await DocumentPage({
      params: Promise.resolve({ documentId: "5c68e652-ab9d-442d-a5b3-d24b015155ad" }),
    });
    render(jsx);

    expect(screen.getByText("Explains the document.")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Analyze document" })
    ).not.toBeInTheDocument();
  });

  it("never offers analysis for an OCR-required document", async () => {
    fetchDocumentMock.mockResolvedValueOnce(validDocument({ status: "ocr_required" }));
    loadAnalysisMock.mockResolvedValueOnce({ status: "none" });

    const jsx = await DocumentPage({
      params: Promise.resolve({ documentId: "5c68e652-ab9d-442d-a5b3-d24b015155ad" }),
    });
    render(jsx);

    expect(
      screen.queryByRole("button", { name: "Analyze document" })
    ).not.toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("No usable text");
  });

  it("shows a localized analysis error while still rendering the document", async () => {
    fetchDocumentMock.mockResolvedValueOnce(validDocument());
    loadAnalysisMock.mockResolvedValueOnce({
      status: "error",
      message: "The analysis service returned an unexpected error.",
    });

    const jsx = await DocumentPage({
      params: Promise.resolve({ documentId: "5c68e652-ab9d-442d-a5b3-d24b015155ad" }),
    });
    render(jsx);

    expect(screen.getByRole("heading", { name: "contract.pdf" })).toBeInTheDocument();
    expect(screen.getByText(/unexpected error/)).toBeInTheDocument();
  });

  it("still calls notFound() for a missing document even when analysis loading fails", async () => {
    fetchDocumentMock.mockRejectedValueOnce(
      new BackendError("not_found", "Document not found.", 404)
    );
    loadAnalysisMock.mockResolvedValueOnce({
      status: "error",
      message: "boom",
    });

    await expect(
      DocumentPage({ params: Promise.resolve({ documentId: "missing" }) })
    ).rejects.toBeInstanceOf(NotFoundSignal);
  });

  it("labels a precomputed demo and replaces live Q&A with curated selections", async () => {
    fetchDocumentMock.mockResolvedValueOnce(validDocument({
      demo_slug: "sample-generic-report",
      demo_questions: [{ id: "missing", question: "What is missing?", status: "insufficient_evidence", answer: "Not provided.", citations: [] }],
    }));
    loadAnalysisMock.mockResolvedValueOnce({ status: "ready", analysis: validAnalysis() });
    const jsx = await DocumentPage({ params: Promise.resolve({ documentId: "5c68e652-ab9d-442d-a5b3-d24b015155ad" }) });
    render(jsx);
    expect(screen.getByText("Precomputed demo")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "What is missing?" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Prepare Q&A" })).not.toBeInTheDocument();
  });
});
