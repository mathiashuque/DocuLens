import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

import { UploadForm } from "@/components/UploadForm";

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
    id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    filename: "doc.pdf",
    content_hash: "a".repeat(64),
    status: "parsed",
    page_count: 1,
    created_at: "2026-08-29T12:34:56+00:00",
    pages: [{ page_number: 1, text: "hello" }],
    sections: [],
  };
}

describe("UploadForm", () => {
  beforeEach(() => {
    pushMock.mockClear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("disables submission until a file is selected", () => {
    render(<UploadForm />);

    expect(screen.getByRole("button", { name: "Upload document" })).toBeDisabled();
  });

  it("shows the selected filename and a human-readable size", async () => {
    const user = userEvent.setup();
    render(<UploadForm />);

    await user.upload(screen.getByLabelText("PDF document"), pdfFile("report.pdf", 2048));

    expect(screen.getByText(/report\.pdf/)).toBeInTheDocument();
    expect(screen.getByText(/2(\.0)? KB/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload document" })).toBeEnabled();
  });

  it("rejects a non-PDF file client-side without a network call", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    // Real browsers still fire onChange for a file chosen via "All Files" in
    // the picker even when `accept` doesn't match, so disable user-event's
    // accept emulation to exercise that path.
    const user = userEvent.setup({ applyAccept: false });
    render(<UploadForm />);

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
    render(<UploadForm />);

    await user.upload(screen.getByLabelText("PDF document"), pdfFile("big.pdf", 11 * 1024 * 1024));

    expect(screen.getByRole("alert")).toHaveTextContent("larger than 10 MB");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("submits once, disables the button, and navigates on success", async () => {
    let resolveFetch: (value: Response) => void = () => {};
    const fetchMock = vi.fn().mockReturnValue(
      new Promise<Response>((resolve) => {
        resolveFetch = resolve;
      })
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<UploadForm />);

    await user.upload(screen.getByLabelText("PDF document"), pdfFile());
    await user.click(screen.getByRole("button", { name: "Upload document" }));

    expect(screen.getByRole("button", { name: "Uploading…" })).toBeDisabled();

    resolveFetch(jsonResponse(201, validDocumentBody()));

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith(
        "/documents/5c68e652-ab9d-442d-a5b3-d24b015155ad"
      );
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("shows a message and restores controls on a 413 response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(413, {})));
    const user = userEvent.setup();
    render(<UploadForm />);

    const file = pdfFile();
    await user.upload(screen.getByLabelText("PDF document"), file);
    await user.click(screen.getByRole("button", { name: "Upload document" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("10 MB");
    });
    expect(screen.getByRole("button", { name: "Upload document" })).toBeEnabled();
    expect(screen.getByText(new RegExp(file.name))).toBeInTheDocument();
  });

  it("shows a message on a 415 response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(415, {})));
    const user = userEvent.setup();
    render(<UploadForm />);

    await user.upload(screen.getByLabelText("PDF document"), pdfFile());
    await user.click(screen.getByRole("button", { name: "Upload document" }));

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
    render(<UploadForm />);

    await user.upload(screen.getByLabelText("PDF document"), pdfFile());
    await user.click(screen.getByRole("button", { name: "Upload document" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Encrypted PDFs are not supported."
      );
    });
  });

  it("shows a generic message on network failure and does not navigate", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));
    const user = userEvent.setup();
    render(<UploadForm />);

    await user.upload(screen.getByLabelText("PDF document"), pdfFile());
    await user.click(screen.getByRole("button", { name: "Upload document" }));

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
    render(<UploadForm />);

    await user.upload(screen.getByLabelText("PDF document"), pdfFile());
    await user.click(screen.getByRole("button", { name: "Upload document" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  it("prevents a double submission from issuing two requests", async () => {
    let resolveFetch: (value: Response) => void = () => {};
    const fetchMock = vi.fn().mockReturnValue(
      new Promise<Response>((resolve) => {
        resolveFetch = resolve;
      })
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<UploadForm />);

    await user.upload(screen.getByLabelText("PDF document"), pdfFile());
    const button = screen.getByRole("button", { name: "Upload document" });
    await user.click(button);
    await user.click(screen.getByRole("button", { name: "Uploading…" }));

    resolveFetch(jsonResponse(201, validDocumentBody()));
    await waitFor(() => expect(pushMock).toHaveBeenCalled());

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
