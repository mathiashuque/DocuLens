"use client";

import { useEffect, useId, useRef, useState } from "react";

import { triggerAnalysis } from "@/lib/analysis-actions";
import type { Analysis } from "@/lib/analysis-schema";

type ButtonState =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "error"; message: string };

export function AnalyzeButton({
  documentId,
  onSuccess,
}: {
  documentId: string;
  onSuccess: (analysis: Analysis) => void;
}) {
  const [state, setState] = useState<ButtonState>({ status: "idle" });
  const errorRef = useRef<HTMLParagraphElement>(null);
  const errorId = useId();
  const isSubmitting = state.status === "submitting";

  useEffect(() => {
    if (state.status === "error") {
      errorRef.current?.focus();
    }
  }, [state]);

  async function handleClick() {
    if (isSubmitting) {
      return;
    }

    setState({ status: "submitting" });
    const result = await triggerAnalysis(documentId);

    if (result.ok) {
      onSuccess(result.analysis);
      setState({ status: "idle" });
      return;
    }

    setState({ status: "error", message: result.message });
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={isSubmitting}
        aria-describedby={state.status === "error" ? errorId : undefined}
        className="inline-flex w-fit items-center justify-center rounded-md bg-zinc-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-zinc-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSubmitting ? "Analyzing…" : "Analyze document"}
      </button>

      <p aria-live="polite" className="sr-only">
        {isSubmitting ? "Analyzing document." : ""}
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
    </div>
  );
}
