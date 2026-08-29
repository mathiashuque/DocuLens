import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

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

function validDocument() {
  return {
    id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    filename: "contract.pdf",
    content_hash: "a".repeat(64),
    status: "parsed" as const,
    page_count: 1,
    created_at: "2026-08-29T12:34:56+00:00",
    pages: [{ page_number: 1, text: "hello" }],
    sections: [],
  };
}

describe("DocumentPage", () => {
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
});
