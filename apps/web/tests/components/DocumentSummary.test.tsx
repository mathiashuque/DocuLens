import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DocumentSummary } from "@/components/DocumentSummary";
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

describe("DocumentSummary", () => {
  it("renders filename, status, page count, and creation time", () => {
    render(<DocumentSummary document={baseDocument()} />);

    expect(screen.getByRole("heading", { name: "contract.pdf" })).toBeInTheDocument();
    expect(screen.getByText("Parsed")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("shows the OCR warning only when status is ocr_required", () => {
    render(<DocumentSummary document={baseDocument({ status: "ocr_required" })} />);

    expect(screen.getByText("OCR required")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/OCR is not yet supported/);
  });

  it("does not show the OCR warning for a parsed document", () => {
    render(<DocumentSummary document={baseDocument()} />);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
