import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AskDocuLens } from "@/components/questions/AskDocuLens";

const DOCUMENT_ID = "5c68e652-ab9d-442d-a5b3-d24b015155ad";
const citationId = "1a5501f3-425d-4d34-b7e2-7db61e37351e";
const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

function renderPanel(pages = [1, 2]) {
  return render(<AskDocuLens documentId={DOCUMENT_ID} documentStatus="parsed" documentPageNumbers={pages} />);
}

function composerInput() {
  return screen.getByLabelText("Ask anything about this document");
}

function sendButton() {
  return screen.getByRole("button", { name: "Send question" });
}

async function askReadyQuestion(user: ReturnType<typeof userEvent.setup>, question: string) {
  await user.type(composerInput(), question);
  await user.click(sendButton());
}

describe("AskDocuLens", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("prepares automatically on mount with no manual Prepare Q&A step", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json(200, { document_id: DOCUMENT_ID, status: "completed" }));
    vi.stubGlobal("fetch", fetchMock);
    renderPanel();

    expect(screen.getByRole("status")).toHaveTextContent("Preparing this document for Q&A");
    await screen.findByLabelText("Ask anything about this document");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: "Prepare Q&A" })).not.toBeInTheDocument();
  });

  it("shows the empty-state welcome and example prompts before the first turn", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(json(200, { document_id: DOCUMENT_ID, status: "completed" })));
    renderPanel();

    expect(await screen.findByRole("heading", { name: "What would you like to know?" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Summarize this document" })).toBeInTheDocument();
  });

  it("populates the composer from an example prompt without submitting it", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(json(200, { document_id: DOCUMENT_ID, status: "completed" })));
    const user = userEvent.setup();
    renderPanel();
    await screen.findByRole("heading", { name: "What would you like to know?" });

    await user.click(screen.getByRole("button", { name: "Identify the main risks" }));

    expect(composerInput()).toHaveValue("Identify the main risks");
    expect(screen.getByRole("heading", { name: "What would you like to know?" })).toBeInTheDocument();
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
    await screen.findByLabelText("Ask anything about this document");
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
    await screen.findByLabelText("Ask anything about this document");

    await askReadyQuestion(user, "What applies?");
    await screen.findByText("The policy applies.");
    expect(screen.getByText("Page 2")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /page 2/i })).not.toBeInTheDocument();

    await askReadyQuestion(user, "What is absent?");
    await screen.findByText("Insufficient evidence");

    // the first turn's answer remains visible alongside the new one
    expect(screen.getByText("The policy applies.")).toBeInTheDocument();
    expect(within(screen.getByRole("log")).getByRole("list", { name: "Answer citations" })).toBeInTheDocument();
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
    await screen.findByLabelText("Ask anything about this document");

    await askReadyQuestion(user, "What applies?");
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
    await screen.findByLabelText("Ask anything about this document");

    await askReadyQuestion(user, "What applies?");

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Prepare Q&A before asking a question."));
    expect(screen.getByRole("button", { name: "Retry preparation" })).toBeInTheDocument();
  });

  it("submits on Enter and inserts a newline on Shift+Enter", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json(200, { document_id: DOCUMENT_ID, status: "completed" }))
      .mockResolvedValueOnce(json(200, {
        document_id: DOCUMENT_ID, question: "Line one\nLine two", status: "answered", answer: "Noted.",
        citations: [{ chunk_id: citationId, page: 1, evidence: "text" }],
      }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderPanel();
    await screen.findByLabelText("Ask anything about this document");

    const input = composerInput();
    await user.type(input, "Line one");
    await user.keyboard("{Shift>}{Enter}{/Shift}");
    await user.type(input, "Line two");
    expect(input).toHaveValue("Line one\nLine two");

    await user.keyboard("{Enter}");
    await screen.findByText("Noted.");
  });

  it("disables sending while a question is pending and does not duplicate the request", async () => {
    let resolveAnswer: (value: Response) => void = () => {};
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json(200, { document_id: DOCUMENT_ID, status: "completed" }))
      .mockReturnValueOnce(new Promise<Response>((resolve) => { resolveAnswer = resolve; }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderPanel();
    await screen.findByLabelText("Ask anything about this document");

    await user.type(composerInput(), "What applies?");
    await user.click(sendButton());
    expect(sendButton()).toBeDisabled();
    await user.click(sendButton());

    resolveAnswer(json(200, {
      document_id: DOCUMENT_ID, question: "What applies?", status: "answered", answer: "Answer.",
      citations: [{ chunk_id: citationId, page: 1, evidence: "text" }],
    }));
    await screen.findByText("Answer.");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("offers Jump to latest instead of force-scrolling when the reader has scrolled up", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json(200, { document_id: DOCUMENT_ID, status: "completed" }))
      .mockResolvedValueOnce(json(200, {
        document_id: DOCUMENT_ID, question: "What applies?", status: "answered", answer: "First answer.",
        citations: [{ chunk_id: citationId, page: 1, evidence: "text" }],
      }))
      .mockResolvedValueOnce(json(200, {
        document_id: DOCUMENT_ID, question: "What else?", status: "answered", answer: "Second answer.",
        citations: [{ chunk_id: citationId, page: 1, evidence: "text" }],
      }));
    vi.stubGlobal("fetch", fetchMock);
    const scrollIntoView = vi.fn();
    window.HTMLElement.prototype.scrollIntoView = scrollIntoView;
    const user = userEvent.setup();
    renderPanel([1]);
    await screen.findByLabelText("Ask anything about this document");

    await askReadyQuestion(user, "What applies?");
    await screen.findByText("First answer.");
    scrollIntoView.mockClear();

    const transcript = screen.getByRole("log");
    Object.defineProperty(transcript, "scrollHeight", { value: 1000, configurable: true });
    Object.defineProperty(transcript, "clientHeight", { value: 200, configurable: true });
    Object.defineProperty(transcript, "scrollTop", { value: 0, configurable: true });
    transcript.dispatchEvent(new Event("scroll"));

    await askReadyQuestion(user, "What else?");
    await screen.findByText("Second answer.");

    const jumpButton = await screen.findByRole("button", { name: /Jump to latest/ });
    expect(scrollIntoView).not.toHaveBeenCalled();

    await user.click(jumpButton);
    expect(scrollIntoView).toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: /Jump to latest/ })).not.toBeInTheDocument();
  });
});
