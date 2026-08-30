import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

import { UploadForm } from "@/components/UploadForm";
import en from "@/lib/i18n/dictionaries/en";

const DOCUMENT_ID = "5c68e652-ab9d-442d-a5b3-d24b015155ad";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function pdfFile(name = "doc.pdf", size = 1024): File {
  const bytes = new Uint8Array(size);
  return new File([bytes], name, { type: "application/pdf" });
}

function validDocumentBody() {
  return {
    id: DOCUMENT_ID,
    filename: "doc.pdf",
    content_hash: "a".repeat(64),
    status: "parsed",
    page_count: 1,
    created_at: "2026-08-29T12:34:56+00:00",
    pages: [{ page_number: 1, text: "hello" }],
    sections: [],
  };
}

function indexCompletedBody() {
  return { document_id: DOCUMENT_ID, status: "completed" };
}

async function uploadAndSubmit(user: ReturnType<typeof userEvent.setup>, file = pdfFile()) {
  await user.upload(screen.getByLabelText("PDF document"), file);
  await user.click(screen.getByRole("button", { name: "Upload document" }));
}

describe("UploadForm", () => {
  beforeEach(() => {
    pushMock.mockClear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("disables submission until a file is selected", () => {
    render(<UploadForm dict={en} lang="en" />);

    expect(screen.getByRole("button", { name: "Upload document" })).toBeDisabled();
  });

  it("shows the selected filename and a human-readable size", async () => {
    const user = userEvent.setup();
    render(<UploadForm dict={en} lang="en" />);

    await user.upload(screen.getByLabelText("PDF document"), pdfFile("report.pdf", 2048));

    expect(screen.getByText(/report\.pdf/)).toBeInTheDocument();
    expect(screen.getByText(/2(\.0)? KB/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload document" })).toBeEnabled();
  });

  it("lets the user change the selected file via the Change action", async () => {
    const user = userEvent.setup();
    render(<UploadForm dict={en} lang="en" />);

    await user.upload(screen.getByLabelText("PDF document"), pdfFile("first.pdf"));
    expect(screen.getByText("first.pdf")).toBeInTheDocument();

    await user.upload(screen.getByLabelText("PDF document"), pdfFile("second.pdf"));
    await user.click(screen.getByRole("button", { name: "Change" }));

    expect(screen.getByText("second.pdf")).toBeInTheDocument();
    expect(screen.queryByText("first.pdf")).not.toBeInTheDocument();
  });

  it("lets the user remove the selected file and returns to the dropzone", async () => {
    const user = userEvent.setup();
    render(<UploadForm dict={en} lang="en" />);

    await user.upload(screen.getByLabelText("PDF document"), pdfFile("report.pdf"));
    await user.click(screen.getByRole("button", { name: "Remove" }));

    expect(screen.queryByText("report.pdf")).not.toBeInTheDocument();
    expect(screen.getByText(/Drop a PDF here/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload document" })).toBeDisabled();
  });

  it("accepts a valid PDF dropped onto the dropzone", async () => {
    render(<UploadForm dict={en} lang="en" />);
    const dropzone = screen.getByText(/Drop a PDF here/).closest("label");
    expect(dropzone).not.toBeNull();

    fireEvent.drop(dropzone!, { dataTransfer: { files: [pdfFile("dropped.pdf")] } });

    expect(await screen.findByText("dropped.pdf")).toBeInTheDocument();
  });

  it("rejects a non-PDF file dropped onto the dropzone without a network call", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<UploadForm dict={en} lang="en" />);
    const dropzone = screen.getByText(/Drop a PDF here/).closest("label");

    const textFile = new File(["hello"], "notes.txt", { type: "text/plain" });
    fireEvent.drop(dropzone!, { dataTransfer: { files: [textFile] } });

    expect(await screen.findByRole("alert")).toHaveTextContent("Choose a PDF file.");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects a non-PDF file client-side without a network call", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    // Real browsers still fire onChange for a file chosen via "All Files" in
    // the picker even when `accept` doesn't match, so disable user-event's
    // accept emulation to exercise that path.
    const user = userEvent.setup({ applyAccept: false });
    render(<UploadForm dict={en} lang="en" />);

    const textFile = new File(["hello"], "notes.txt", { type: "text/plain" });
    await user.upload(screen.getByLabelText("PDF document"), textFile);

    expect(screen.getByRole("alert")).toHaveTextContent("Choose a PDF file.");
    expect(screen.getByRole("button", { name: "Upload document" })).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects a file over 10 MB client-side without a network call", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<UploadForm dict={en} lang="en" />);

    await user.upload(screen.getByLabelText("PDF document"), pdfFile("big.pdf", 11 * 1024 * 1024));

    expect(screen.getByRole("alert")).toHaveTextContent("larger than 10 MB");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("uploads, prepares the index, and only then navigates to the ready chat", async () => {
    let resolveUpload: (value: Response) => void = () => {};
    let resolveIndex: (value: Response) => void = () => {};
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(new Promise<Response>((resolve) => { resolveUpload = resolve; }))
      .mockReturnValueOnce(new Promise<Response>((resolve) => { resolveIndex = resolve; }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<UploadForm dict={en} lang="en" />);

    await uploadAndSubmit(user);
    expect(screen.getByRole("button", { name: "Uploading…" })).toBeDisabled();

    resolveUpload(jsonResponse(201, validDocumentBody()));
    await screen.findByRole("button", { name: "Preparing…" });
    expect(pushMock).not.toHaveBeenCalled();

    resolveIndex(jsonResponse(201, indexCompletedBody()));
    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith(`/en/documents/${DOCUMENT_ID}`);
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("shows a message and restores controls on a 413 response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(413, {})));
    const user = userEvent.setup();
    render(<UploadForm dict={en} lang="en" />);

    const file = pdfFile();
    await uploadAndSubmit(user, file);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("10 MB");
    });
    expect(screen.getByRole("button", { name: "Upload document" })).toBeEnabled();
    expect(screen.getByText(new RegExp(file.name))).toBeInTheDocument();
  });

  it("shows a message on a 415 response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(415, {})));
    const user = userEvent.setup();
    render(<UploadForm dict={en} lang="en" />);

    await uploadAndSubmit(user);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("PDF");
    });
  });

  it("shows a message on a 422 response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(422, { message: "Encrypted PDFs are not supported." }))
    );
    const user = userEvent.setup();
    render(<UploadForm dict={en} lang="en" />);

    await uploadAndSubmit(user);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Encrypted PDFs are not supported."
      );
    });
  });

  it("shows a generic message on network failure and does not navigate", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));
    const user = userEvent.setup();
    render(<UploadForm dict={en} lang="en" />);

    await uploadAndSubmit(user);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("shows a generic message on a malformed response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("not json", { status: 201 }))
    );
    const user = userEvent.setup();
    render(<UploadForm dict={en} lang="en" />);

    await uploadAndSubmit(user);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  it("prevents a double submission from issuing two upload requests", async () => {
    let resolveUpload: (value: Response) => void = () => {};
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(
        new Promise<Response>((resolve) => {
          resolveUpload = resolve;
        })
      )
      .mockReturnValueOnce(new Promise<Response>(() => {}));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<UploadForm dict={en} lang="en" />);

    await user.upload(screen.getByLabelText("PDF document"), pdfFile());
    const button = screen.getByRole("button", { name: "Upload document" });
    await user.click(button);
    await user.click(screen.getByRole("button", { name: "Uploading…" }));

    resolveUpload(jsonResponse(201, validDocumentBody()));
    await screen.findByRole("button", { name: "Preparing…" });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/documents");
  });

  it("keeps the document ID and lets the user retry preparation without re-uploading", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(201, validDocumentBody()))
      .mockResolvedValueOnce(jsonResponse(502, { error: "provider_invalid", message: "The embedding service failed to produce a valid result." }))
      .mockResolvedValueOnce(jsonResponse(201, indexCompletedBody()));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<UploadForm dict={en} lang="en" />);

    await uploadAndSubmit(user);
    await screen.findByRole("alert");
    expect(screen.getByRole("alert")).toHaveTextContent("embedding service");

    await user.click(screen.getByRole("button", { name: "Retry preparation" }));
    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith(`/en/documents/${DOCUMENT_ID}`);
    });
    // one upload call plus two index calls; never a second upload
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/documents");
  });
});
