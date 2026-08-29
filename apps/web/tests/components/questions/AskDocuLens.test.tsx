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

  it("does not index on render, prevents duplicate preparation, and enables a question form", async () => {
    let resolveIndex: (value: Response) => void = () => {};
    const fetchMock = vi.fn().mockReturnValue(new Promise<Response>((resolve) => { resolveIndex = resolve; }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderPanel();
    expect(fetchMock).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Prepare Q&A" }));
    expect(screen.getByRole("button", { name: "Preparing Q&A…" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Preparing Q&A…" }));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    resolveIndex(json(201, { document_id: DOCUMENT_ID, status: "completed" }));
    await screen.findByRole("button", { name: "Ask DocuLens" });
  });

  it("renders validated evidence links and keeps insufficient evidence citation-free", async () => {
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
    await user.click(screen.getByRole("button", { name: "Prepare Q&A" }));
    await screen.findByRole("button", { name: "Ask DocuLens" });
    const input = screen.getByLabelText("Your question");
    await user.type(input, "What applies?");
    await user.click(screen.getByRole("button", { name: "Ask DocuLens" }));
    await screen.findByText("The policy applies.");
    expect(screen.getByRole("link", { name: "View page 2" })).toHaveAttribute("href", "#page-2");
    await user.clear(input);
    await user.type(input, "What is absent?");
    await user.click(screen.getByRole("button", { name: "Ask DocuLens" }));
    await screen.findByText("Insufficient evidence");
    expect(screen.queryByRole("list", { name: "Answer citations" })).not.toBeInTheDocument();
  });

  it("fails closed when a citation page is absent and returns to preparation when an index is missing", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json(200, { document_id: DOCUMENT_ID, status: "completed" }))
      .mockResolvedValueOnce(json(200, {
        document_id: DOCUMENT_ID, question: "What applies?", status: "answered", answer: "The policy applies.",
        citations: [{ chunk_id: citationId, page: 3, evidence: "Policy text." }],
      }))
      .mockResolvedValueOnce(json(409, { error: "missing_index", message: "Prepare Q&A before asking a question." }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderPanel([1]);
    await user.click(screen.getByRole("button", { name: "Prepare Q&A" }));
    await screen.findByRole("button", { name: "Ask DocuLens" });
    const input = screen.getByLabelText("Your question");
    await user.type(input, "What applies?");
    await user.click(screen.getByRole("button", { name: "Ask DocuLens" }));
    await screen.findByRole("alert");
    expect(screen.queryByText("The policy applies.")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Ask DocuLens" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Prepare Q&A" })).toBeInTheDocument());
  });
});
