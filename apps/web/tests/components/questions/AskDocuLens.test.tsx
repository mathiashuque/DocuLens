import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AskDocuLens } from "@/components/questions/AskDocuLens";

const DOCUMENT_ID = "5c68e652-ab9d-442d-a5b3-d24b015155ad";
const citationId = "1a5501f3-425d-4d34-b7e2-7db61e37351e";
const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

function renderPanel(pages = [1, 2]) {
  return render(<AskDocuLens documentId={DOCUMENT_ID} documentStatus="parsed" documentPageNumbers={pages} />);
}

describe("AskDocuLens", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("prepares automatically on mount with no manual Prepare Q&A step", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json(200, { document_id: DOCUMENT_ID, status: "completed" }));
    vi.stubGlobal("fetch", fetchMock);
    renderPanel();

    expect(screen.getByRole("status")).toHaveTextContent("Preparing this document for Q&A");
    await screen.findByRole("button", { name: "Ask DocuLens" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: "Prepare Q&A" })).not.toBeInTheDocument();
  });

  it("shows a retryable error and does not duplicate preparation calls while retrying", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json(502, { error: "provider_invalid", message: "The embedding service failed." }))
      .mockResolvedValueOnce(json(200, { document_id: DOCUMENT_ID, status: "completed" }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderPanel();

    await screen.findByRole("alert");
    expect(screen.getByRole("alert")).toHaveTextContent("The embedding service failed.");
    await user.click(screen.getByRole("button", { name: "Retry preparation" }));
    await screen.findByRole("button", { name: "Ask DocuLens" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("does not offer a retry for an ineligible document", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(json(409, { error: "ineligible_document", message: "This document is not eligible for Q&A." })));
    renderPanel();

    await screen.findByRole("alert");
    expect(screen.queryByRole("button", { name: "Retry preparation" })).not.toBeInTheDocument();
  });

  it("keeps prior turns visible and renders inline page evidence without page-anchor links", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json(200, { document_id: DOCUMENT_ID, status: "completed" }))
      .mockResolvedValueOnce(json(200, {
        document_id: DOCUMENT_ID, question: "What applies?", status: "answered", answer: "The policy applies.",
        citations: [{ chunk_id: citationId, page: 2, evidence: "Policy text." }],
      }))
      .mockResolvedValueOnce(json(200, {
        document_id: DOCUMENT_ID, question: "What is absent?", status: "insufficient_evidence", answer: "The document does not say.", citations: [],
      }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderPanel();
    await screen.findByRole("button", { name: "Ask DocuLens" });

    const input = screen.getByLabelText("Your question");
    await user.type(input, "What applies?");
    await user.click(screen.getByRole("button", { name: "Ask DocuLens" }));
    await screen.findByText("The policy applies.");
    expect(screen.getByText("Page 2")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /page 2/i })).not.toBeInTheDocument();

    await user.clear(input);
    await user.type(input, "What is absent?");
    await user.click(screen.getByRole("button", { name: "Ask DocuLens" }));
    await screen.findByText("Insufficient evidence");

    // the first turn's answer remains visible alongside the new one
    expect(screen.getByText("The policy applies.")).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Answer citations" })).toBeInTheDocument();
  });

  it("fails closed when a citation page is absent from the document", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json(200, { document_id: DOCUMENT_ID, status: "completed" }))
      .mockResolvedValueOnce(json(200, {
        document_id: DOCUMENT_ID, question: "What applies?", status: "answered", answer: "The policy applies.",
        citations: [{ chunk_id: citationId, page: 3, evidence: "Policy text." }],
      }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderPanel([1]);
    await screen.findByRole("button", { name: "Ask DocuLens" });

    const input = screen.getByLabelText("Your question");
    await user.type(input, "What applies?");
    await user.click(screen.getByRole("button", { name: "Ask DocuLens" }));
    await screen.findByRole("alert");
    expect(screen.queryByText("The policy applies.")).not.toBeInTheDocument();
  });

  it("returns to a recoverable preparation state when the index goes missing mid-session", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json(200, { document_id: DOCUMENT_ID, status: "completed" }))
      .mockResolvedValueOnce(json(409, { error: "missing_index", message: "Prepare Q&A before asking a question." }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderPanel();
    await screen.findByRole("button", { name: "Ask DocuLens" });

    const input = screen.getByLabelText("Your question");
    await user.type(input, "What applies?");
    await user.click(screen.getByRole("button", { name: "Ask DocuLens" }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Prepare Q&A before asking a question."));
    expect(screen.getByRole("button", { name: "Retry preparation" })).toBeInTheDocument();
  });
});
