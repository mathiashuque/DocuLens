import { describe, expect, it } from "vitest";

import {
  parseQuestionResponseForDocument,
  questionRequestSchema,
} from "@/lib/question-schema";

const DOCUMENT_ID = "5c68e652-ab9d-442d-a5b3-d24b015155ad";
const citation = {
  chunk_id: "1a5501f3-425d-4d34-b7e2-7db61e37351e",
  page: 1,
  evidence: "The document says this.",
};

describe("grounded Q&A schemas", () => {
  it("rejects blank, oversized, and extra question request fields", () => {
    expect(questionRequestSchema.safeParse({ question: "   " }).success).toBe(false);
    expect(questionRequestSchema.safeParse({ question: "a".repeat(2001) }).success).toBe(false);
    expect(questionRequestSchema.safeParse({ question: "What applies?", top_k: 20 }).success).toBe(false);
  });

  it("rejects malformed, mismatched, and unsupported answer shapes", () => {
    const base = { document_id: DOCUMENT_ID, question: "What applies?", answer: "An answer." };
    expect(parseQuestionResponseForDocument(DOCUMENT_ID, { ...base, status: "answered", citations: [] }).success).toBe(false);
    expect(parseQuestionResponseForDocument(DOCUMENT_ID, { ...base, status: "insufficient_evidence", citations: [citation] }).success).toBe(false);
    expect(parseQuestionResponseForDocument(DOCUMENT_ID, { ...base, status: "answered", citations: [{ ...citation, page: 0 }] }).success).toBe(false);
    expect(parseQuestionResponseForDocument(DOCUMENT_ID, { ...base, status: "answered", citations: [{ ...citation, evidence: " " }] }).success).toBe(false);
    expect(parseQuestionResponseForDocument("d49f6cf2-5095-4d66-a659-f3c0ea941abc", { ...base, status: "answered", citations: [citation] }).success).toBe(false);
  });
});
