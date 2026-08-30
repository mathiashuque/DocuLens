import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

const { fetchDocumentMock, notFoundMock, NotFoundSignal } = vi.hoisted(() => {
  class HoistedNotFoundSignal extends Error {}
  return {
    fetchDocumentMock: vi.fn(),
    notFoundMock: vi.fn(() => {
      throw new HoistedNotFoundSignal("NEXT_NOT_FOUND");
    }),
    NotFoundSignal: HoistedNotFoundSignal,
  };
});

vi.mock("@/lib/backend-client", () => ({
  fetchDocument: fetchDocumentMock,
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

describe("DocumentPage", () => {
  beforeEach(() => {
    fetchDocumentMock.mockReset();
    notFoundMock.mockClear();
  });

  it("renders a compact chat workspace with the document's filename", async () => {
    fetchDocumentMock.mockResolvedValueOnce(validDocument());

    const jsx = await DocumentPage({
      params: Promise.resolve({ documentId: "5c68e652-ab9d-442d-a5b3-d24b015155ad" }),
    });
    render(jsx);

    expect(screen.getByRole("heading", { name: "contract.pdf" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Ask DocuLens" })).toBeInTheDocument();
  });

  it("never renders document structure, raw page text, or page counts", async () => {
    fetchDocumentMock.mockResolvedValueOnce(validDocument());

    const jsx = await DocumentPage({
      params: Promise.resolve({ documentId: "5c68e652-ab9d-442d-a5b3-d24b015155ad" }),
    });
    render(jsx);

    expect(screen.queryByText("Page 1")).not.toBeInTheDocument();
    expect(screen.queryByText(/Pages:/)).not.toBeInTheDocument();
    expect(screen.queryByText("hello")).not.toBeInTheDocument();
    expect(screen.queryByText(/No reliable headings were detected/)).not.toBeInTheDocument();
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

  it("shows the question composer for a parsed document with no dependency on analysis", async () => {
    fetchDocumentMock.mockResolvedValueOnce(validDocument());

    const jsx = await DocumentPage({
      params: Promise.resolve({ documentId: "5c68e652-ab9d-442d-a5b3-d24b015155ad" }),
    });
    render(jsx);

    expect(screen.getByRole("region", { name: "Ask DocuLens" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Analyze document" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Prepare Q&A" })).not.toBeInTheDocument();
  });

  it("shows an OCR alert instead of the question composer for an OCR-required document", async () => {
    fetchDocumentMock.mockResolvedValueOnce(validDocument({ status: "ocr_required" }));

    const jsx = await DocumentPage({
      params: Promise.resolve({ documentId: "5c68e652-ab9d-442d-a5b3-d24b015155ad" }),
    });
    render(jsx);

    expect(screen.queryByRole("region", { name: "Ask DocuLens" })).not.toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("No usable text");
  });

  it("labels a precomputed demo and replaces live Q&A with curated selections", async () => {
    fetchDocumentMock.mockResolvedValueOnce(validDocument({
      demo_slug: "sample-generic-report",
      demo_questions: [{ id: "missing", question: "What is missing?", status: "insufficient_evidence", answer: "Not provided.", citations: [] }],
    }));
    const jsx = await DocumentPage({ params: Promise.resolve({ documentId: "5c68e652-ab9d-442d-a5b3-d24b015155ad" }) });
    render(jsx);
    expect(screen.getByText("Precomputed demo")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "What is missing?" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Prepare Q&A" })).not.toBeInTheDocument();
  });
});
