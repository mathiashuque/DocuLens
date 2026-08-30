"use client";

import {
  useEffect,
  useId,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
} from "react";
import { useRouter } from "next/navigation";

import { Reveal } from "@/components/motion/primitives";
import type { Dictionary } from "@/lib/i18n/dictionary";
import type { Locale } from "@/lib/i18n/locales";
import { formatBytes } from "@/lib/format";
import { ACCEPTED_CONTENT_TYPE, MAX_UPLOAD_BYTES, uploadDocument } from "@/lib/upload";
import { prepareQuestionAnswering } from "@/lib/question-actions";

type FormState =
  | { status: "idle" }
  | { status: "uploading" }
  | { status: "preparing"; documentId: string }
  | { status: "error"; message: string; retryDocumentId?: string };

function FileIcon() {
  return (
    <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M3.5 1.5h6l3 3v10a.5.5 0 0 1-.5.5h-8.5a.5.5 0 0 1-.5-.5v-12a.5.5 0 0 1 .5-.5Z" />
      <path d="M9.5 1.5v3h3" />
    </svg>
  );
}

export function UploadForm({ dict, lang }: { dict: Dictionary; lang: Locale }) {
  const t = dict.upload;
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<FormState>({ status: "idle" });
  const [isDragOver, setIsDragOver] = useState(false);
  const errorRef = useRef<HTMLParagraphElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const errorId = useId();
  const inputId = useId();

  const busy = state.status === "uploading" || state.status === "preparing";

  useEffect(() => {
    if (state.status === "error") {
      errorRef.current?.focus();
    }
  }, [state]);

  function acceptFile(selected: File): boolean {
    if (selected.type !== ACCEPTED_CONTENT_TYPE) {
      setFile(null);
      setState({ status: "error", message: t.errorChooseFile });
      return false;
    }

    if (selected.size > MAX_UPLOAD_BYTES) {
      setFile(null);
      setState({ status: "error", message: t.errorTooLarge });
      return false;
    }

    setFile(selected);
    setState({ status: "idle" });
    return true;
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0];
    if (!selected) return;
    const accepted = acceptFile(selected);
    if (!accepted) event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragOver(false);
    if (busy) return;
    const dropped = event.dataTransfer.files[0];
    if (dropped) acceptFile(dropped);
  }

  function handleRemove() {
    setFile(null);
    setState({ status: "idle" });
    if (inputRef.current) inputRef.current.value = "";
  }

  async function prepareAndEnter(documentId: string) {
    setState({ status: "preparing", documentId });
    const result = await prepareQuestionAnswering(documentId, dict.errors, lang);
    if (result.ok) {
      router.push(`/${lang}/documents/${documentId}`);
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
    const result = await uploadDocument(file, t);

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
      {file ? (
        <div className="flex items-center gap-3 rounded-md border border-hairline bg-surface-muted px-4 py-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-accent-soft text-accent-strong">
            <FileIcon />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-ink">{file.name}</p>
            <p className="text-xs text-ink-subtle">{formatBytes(file.size)}</p>
          </div>
          <div className="flex shrink-0 gap-1">
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              disabled={busy}
              className="rounded-md px-2 py-1.5 text-xs font-medium text-ink-muted hover:bg-canvas-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t.change}
            </button>
            <button
              type="button"
              onClick={handleRemove}
              disabled={busy}
              className="rounded-md px-2 py-1.5 text-xs font-medium text-ink-muted hover:bg-canvas-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t.remove}
            </button>
          </div>
        </div>
      ) : (
        <label
          htmlFor={inputId}
          onDragOver={(event) => { event.preventDefault(); if (!busy) setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          className={`flex cursor-pointer flex-col items-center gap-1.5 rounded-md border-2 border-dashed px-4 py-8 text-center transition-colors focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-accent ${
            isDragOver ? "border-accent bg-accent-soft" : "border-hairline hover:border-accent/40"
          }`}
        >
          <span className="text-sm font-medium text-ink">
            {t.dropPrefix} <span className="text-accent underline underline-offset-2">{t.browse}</span>
          </span>
          <span className="text-xs text-ink-subtle">{t.sizeHint}</span>
        </label>
      )}

      <input
        ref={inputRef}
        id={inputId}
        name="file"
        type="file"
        accept="application/pdf,.pdf"
        aria-label={t.fileInputAriaLabel}
        onChange={handleFileChange}
        disabled={busy}
        aria-describedby={state.status === "error" ? errorId : undefined}
        className="sr-only"
      />

      <button
        type="submit"
        disabled={!file || busy}
        className="inline-flex w-fit items-center justify-center rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50 motion-safe:active:scale-[0.98]"
      >
        {state.status === "uploading" ? t.uploading : state.status === "preparing" ? t.preparing : t.uploadButton}
      </button>

      <p aria-live="polite" className="sr-only">
        {state.status === "uploading" ? t.liveUploading : ""}
        {state.status === "preparing" ? t.livePreparing : ""}
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
                <div className="flex flex-col gap-1.5">
                  <p className="text-xs text-ink-subtle">{t.errorAlreadyUploadedRetry}</p>
                  <button
                    type="button"
                    onClick={() => handleRetryPreparation(retryDocumentId)}
                    className="inline-flex w-fit items-center justify-center rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent motion-safe:active:scale-[0.98]"
                  >
                    {t.retryPreparation}
                  </button>
                </div>
              );
            })()}
          </div>
        </Reveal>
      ) : null}
    </form>
  );
}
