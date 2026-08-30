"use client";

import { useEffect, useId, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { Reveal } from "@/components/motion/primitives";
import { formatBytes } from "@/lib/format";
import { ACCEPTED_CONTENT_TYPE, MAX_UPLOAD_BYTES, uploadDocument } from "@/lib/upload";
import { prepareQuestionAnswering } from "@/lib/question-actions";

type FormState =
  | { status: "idle" }
  | { status: "uploading" }
  | { status: "preparing"; documentId: string }
  | { status: "error"; message: string; retryDocumentId?: string };

export function UploadForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<FormState>({ status: "idle" });
  const errorRef = useRef<HTMLParagraphElement>(null);
  const errorId = useId();

  const busy = state.status === "uploading" || state.status === "preparing";

  useEffect(() => {
    if (state.status === "error") {
      errorRef.current?.focus();
    }
  }, [state]);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;

    if (!selected) {
      setFile(null);
      setState({ status: "idle" });
      return;
    }

    if (selected.type !== ACCEPTED_CONTENT_TYPE) {
      setFile(null);
      setState({ status: "error", message: "Choose a PDF file." });
      event.target.value = "";
      return;
    }

    if (selected.size > MAX_UPLOAD_BYTES) {
      setFile(null);
      setState({ status: "error", message: "That file is larger than 10 MB." });
      event.target.value = "";
      return;
    }

    setFile(selected);
    setState({ status: "idle" });
  }

  async function prepareAndEnter(documentId: string) {
    setState({ status: "preparing", documentId });
    const result = await prepareQuestionAnswering(documentId);
    if (result.ok) {
      router.push(`/documents/${documentId}`);
      return;
    }
    setState({
      status: "error",
      message: result.message,
      retryDocumentId: documentId,
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || busy) {
      return;
    }

    setState({ status: "uploading" });
    const result = await uploadDocument(file);

    if (!result.ok) {
      setState({ status: "error", message: result.message });
      return;
    }

    await prepareAndEnter(result.document.id);
  }

  async function handleRetryPreparation(documentId: string) {
    await prepareAndEnter(documentId);
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <label htmlFor="document-file" className="text-sm font-medium text-ink">
          PDF document
        </label>
        <input
          id="document-file"
          name="file"
          type="file"
          accept="application/pdf,.pdf"
          onChange={handleFileChange}
          disabled={busy}
          aria-describedby={state.status === "error" ? errorId : undefined}
          className="block w-full rounded-md border border-zinc-300 text-sm text-ink-muted file:mr-4 file:rounded-md file:border-0 file:bg-accent file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-accent-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-60"
        />
        {file ? (
          <Reveal>
            <p className="text-sm text-ink-muted">
              {file.name} &middot; {formatBytes(file.size)}
            </p>
          </Reveal>
        ) : null}
      </div>

      <button
        type="submit"
        disabled={!file || busy}
        className="inline-flex w-fit items-center justify-center rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50 motion-safe:active:scale-[0.98]"
      >
        {state.status === "uploading" ? "Uploading…" : state.status === "preparing" ? "Preparing…" : "Upload document"}
      </button>

      <p aria-live="polite" className="sr-only">
        {state.status === "uploading" ? "Uploading document." : ""}
        {state.status === "preparing" ? "Preparing document for questions." : ""}
      </p>

      {state.status === "error" ? (
        <Reveal>
          <div className="flex flex-col gap-3">
            <p
              id={errorId}
              ref={errorRef}
              role="alert"
              tabIndex={-1}
              className="text-sm font-medium text-red-700 focus:outline-none"
            >
              {state.message}
            </p>
            {(() => {
              const retryDocumentId = state.retryDocumentId;
              if (!retryDocumentId) return null;
              return (
                <button
                  type="button"
                  onClick={() => handleRetryPreparation(retryDocumentId)}
                  className="inline-flex w-fit items-center justify-center rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent motion-safe:active:scale-[0.98]"
                >
                  Retry preparation
                </button>
              );
            })()}
          </div>
        </Reveal>
      ) : null}
    </form>
  );
}
