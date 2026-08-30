import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DocumentHeader } from "@/components/DocumentHeader";
import type { Document } from "@/lib/document-schema";

function baseDocument(overrides: Partial<Document> = {}): Document {
  return {
    id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    filename: "contract.pdf",
    content_hash: "a".repeat(64),
    status: "parsed",
    page_count: 3,
    created_at: "2026-08-29T12:34:56+00:00",
    pages: [],
    sections: [],
    ...overrides,
  };
}

describe("DocumentHeader", () => {
  it("renders the filename, status, and a link back to upload", () => {
    render(<DocumentHeader document={baseDocument()} />);

    expect(screen.getByRole("heading", { name: "contract.pdf" })).toBeInTheDocument();
    expect(screen.getByText("Parsed")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Upload another document/ })).toHaveAttribute("href", "/");
  });

  it("does not render page counts or upload timestamps", () => {
    render(<DocumentHeader document={baseDocument()} />);

    expect(screen.queryByText(/Pages:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Uploaded:/)).not.toBeInTheDocument();
  });

  it("shows an OCR-required alert when the document has no usable text", () => {
    render(<DocumentHeader document={baseDocument({ status: "ocr_required" })} />);

    expect(screen.getByRole("alert")).toHaveTextContent("No usable text");
  });

  it("shows no alert for a normally parsed document", () => {
    render(<DocumentHeader document={baseDocument()} />);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
