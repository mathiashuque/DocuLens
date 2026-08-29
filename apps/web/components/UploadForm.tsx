"use client";

import { useEffect, useId, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { formatBytes } from "@/lib/format";
import { ACCEPTED_CONTENT_TYPE, MAX_UPLOAD_BYTES, uploadDocument } from "@/lib/upload";

type FormState =
  | { status: "idle" }
  | { status: "uploading" }
  | { status: "error"; message: string };

export function UploadForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [state, setState] = useState<FormState>({ status: "idle" });
  const errorRef = useRef<HTMLParagraphElement>(null);
  const errorId = useId();

  const isUploading = state.status === "uploading";

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

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || isUploading) {
      return;
    }

    setState({ status: "uploading" });
    const result = await uploadDocument(file);

    if (result.ok) {
      router.push(`/documents/${result.document.id}`);
      return;
    }

    setState({ status: "error", message: result.message });
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <label htmlFor="document-file" className="text-sm font-medium text-zinc-900">
          PDF document
        </label>
        <input
          id="document-file"
          name="file"
          type="file"
          accept="application/pdf,.pdf"
          onChange={handleFileChange}
          disabled={isUploading}
          aria-describedby={state.status === "error" ? errorId : undefined}
          className="block w-full rounded-md border border-zinc-300 text-sm text-zinc-700 file:mr-4 file:rounded-md file:border-0 file:bg-zinc-900 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-zinc-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900 disabled:cursor-not-allowed disabled:opacity-60"
        />
        {file ? (
          <p className="text-sm text-zinc-600">
            {file.name} &middot; {formatBytes(file.size)}
          </p>
        ) : null}
      </div>

      <button
        type="submit"
        disabled={!file || isUploading}
        className="inline-flex w-fit items-center justify-center rounded-md bg-zinc-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-zinc-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isUploading ? "Uploading…" : "Upload document"}
      </button>

      <p aria-live="polite" className="sr-only">
        {isUploading ? "Uploading document." : ""}
      </p>

      {state.status === "error" ? (
        <p
          id={errorId}
          ref={errorRef}
          role="alert"
          tabIndex={-1}
          className="text-sm font-medium text-red-700 focus:outline-none"
        >
          {state.message}
        </p>
      ) : null}
    </form>
  );
}
