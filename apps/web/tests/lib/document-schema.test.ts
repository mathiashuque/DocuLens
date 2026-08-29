import { describe, expect, it } from "vitest";

import { parseDocument } from "@/lib/document-schema";

function validDocument() {
  return {
    id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    filename: "contract.pdf",
    content_hash: "a".repeat(64),
    status: "parsed",
    page_count: 2,
    created_at: "2026-08-29T12:34:56.789012+00:00",
    pages: [
      { page_number: 1, text: "First page" },
      { page_number: 2, text: "" },
    ],
    sections: [
      {
        id: "8d68405e-e7e1-4e7f-bb1f-7d42cfc88afd",
        title: "1 Introduction",
        level: 1,
        parent_section_id: null,
        page_start: 1,
        page_end: 1,
        section_path: ["1 Introduction"],
        text: "1 Introduction\nFirst page",
      },
    ],
  };
}

describe("parseDocument", () => {
  it("parses a valid document payload into the typed contract", () => {
    const result = parseDocument(validDocument());

    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.filename).toBe("contract.pdf");
      expect(result.data.sections[0].title).toBe("1 Introduction");
    }
  });

  it("parses a document with no sections", () => {
    const payload = { ...validDocument(), sections: [] };

    const result = parseDocument(payload);

    expect(result.success).toBe(true);
  });

  it("rejects an invalid status value", () => {
    const payload = { ...validDocument(), status: "processing" };

    expect(parseDocument(payload).success).toBe(false);
  });

  it("rejects a non-positive page number", () => {
    const payload = {
      ...validDocument(),
      pages: [{ page_number: 0, text: "x" }],
    };

    expect(parseDocument(payload).success).toBe(false);
  });

  it("rejects a section whose page_end precedes page_start", () => {
    const payload = validDocument();
    payload.sections[0].page_start = 3;
    payload.sections[0].page_end = 1;

    expect(parseDocument(payload).success).toBe(false);
  });

  it("rejects a section with a malformed UUID", () => {
    const payload = validDocument();
    payload.sections[0].id = "not-a-uuid";

    expect(parseDocument(payload).success).toBe(false);
  });

  it("rejects a document with a malformed top-level id", () => {
    const payload = { ...validDocument(), id: "not-a-uuid" };

    expect(parseDocument(payload).success).toBe(false);
  });

  it("rejects missing required fields", () => {
    const withoutPages: Record<string, unknown> = validDocument();
    delete withoutPages.pages;

    expect(parseDocument(withoutPages).success).toBe(false);
  });
});
