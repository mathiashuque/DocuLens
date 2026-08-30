"use client";

import { useEffect, useId, useRef, useState } from "react";

import { EvidenceQuote } from "@/components/analysis/EvidenceQuote";
import { Reveal, StaggerGroup, StaggerItem } from "@/components/motion/primitives";
import {
  askDocumentQuestion,
  prepareQuestionAnswering,
  type QuestionFailureKind,
} from "@/lib/question-actions";
import { MAX_QUESTION_LENGTH, type QuestionResponse } from "@/lib/question-schema";
import type { DocumentStatus } from "@/lib/document-schema";

type PreparationState =
  | { status: "preparing" }
  | { status: "ready" }
  | { status: "error"; kind: QuestionFailureKind; message: string };

type Turn = {
  id: string;
  question: string;
} & (
  | { status: "pending" }
  | { status: "answered" | "insufficient_evidence"; result: QuestionResponse }
  | { status: "error"; message: string }
);

function canRetryPreparation(kind: QuestionFailureKind) {
  return kind !== "ineligible_document" && kind !== "incompatible_index" && kind !== "not_found";
}

function AnswerTurn({ turn }: { turn: Turn }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="ml-auto max-w-[85%] rounded-card bg-accent px-4 py-2.5 text-sm text-white">
        <span className="sr-only">You asked: </span>
        {turn.question}
      </div>

      {turn.status === "pending" ? (
        <div className="mr-auto max-w-[85%] rounded-card border border-zinc-200 bg-zinc-50 px-4 py-2.5 text-sm text-ink-muted" role="status">
          <span className="sr-only">DocuLens is answering.</span>
          Thinking…
        </div>
      ) : null}

      {turn.status === "error" ? (
        <Reveal>
          <p role="alert" className="mr-auto max-w-[85%] rounded-card border border-red-300 bg-red-50 px-4 py-2.5 text-sm font-medium text-red-800">
            {turn.message}
          </p>
        </Reveal>
      ) : null}

      {turn.status === "insufficient_evidence" ? (
        <Reveal>
          <div className="mr-auto max-w-[85%] rounded-card border border-amber-300 bg-amber-50 p-4" role="status">
            <h3 className="font-semibold text-amber-950">Insufficient evidence</h3>
            <p className="mt-1 whitespace-pre-wrap break-words text-sm text-amber-900">{turn.result.answer}</p>
            <p className="mt-2 text-sm text-amber-900">Try rephrasing your question using terms from the document.</p>
          </div>
        </Reveal>
      ) : null}

      {turn.status === "answered" ? (
        <Reveal>
          <div className="mr-auto flex max-w-[85%] flex-col gap-4 rounded-card border border-zinc-200 bg-zinc-50 p-4">
            <p className="whitespace-pre-wrap break-words text-sm text-ink-muted">{turn.result.answer}</p>
            <ol className="flex flex-col gap-3" aria-label="Answer citations">
              {turn.result.citations.map((citation, index) => (
                <li key={citation.chunk_id}>
                  <p className="text-xs font-medium text-ink-subtle">Citation {index + 1}</p>
                  <EvidenceQuote page={citation.page} quote={citation.evidence} />
                </li>
              ))}
            </ol>
          </div>
        </Reveal>
      ) : null}
    </div>
  );
}

/**
 * A single-document chat workspace: preparation is automatic (no manual
 * "Prepare Q&A" step in the normal flow — the upload flow already indexes
 * the document before redirecting here). This effect only does real work
 * for the exceptional case of a direct link or refresh landing on a parsed
 * document whose index is missing or was never completed; the idempotent
 * index call is a safe, free no-op when the document is already indexed.
 */
export function AskDocuLens({
  documentId,
  documentStatus,
  documentPageNumbers,
}: {
  documentId: string;
  documentStatus: DocumentStatus;
  documentPageNumbers: readonly number[];
}) {
  const eligible = documentStatus === "parsed";
  const [preparation, setPreparation] = useState<PreparationState>({ status: "preparing" });
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [questionError, setQuestionError] = useState<string | null>(null);
  const questionId = useId();
  const questionErrorId = useId();
  const preparingRef = useRef(false);
  const answering = turns.some((turn) => turn.status === "pending");

  async function prepare() {
    if (preparingRef.current) return;
    preparingRef.current = true;
    setPreparation({ status: "preparing" });
    const result = await prepareQuestionAnswering(documentId);
    preparingRef.current = false;
    setPreparation(result.ok ? { status: "ready" } : { status: "error", kind: result.kind, message: result.message });
  }

  useEffect(() => {
    if (eligible) void prepare();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId, eligible]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (answering) return;
    if (!trimmed) {
      setQuestionError("Enter a question before asking DocuLens.");
      return;
    }
    setQuestionError(null);
    const turnId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setTurns((prev) => [...prev, { id: turnId, question: trimmed, status: "pending" }]);
    setQuestion("");

    const result = await askDocumentQuestion(documentId, trimmed);

    if (result.ok) {
      if (!result.data.citations.every((citation) => documentPageNumbers.includes(citation.page))) {
        setTurns((prev) => prev.map((turn) => turn.id === turnId
          ? { id: turnId, question: trimmed, status: "error", message: "The Q&A service returned a citation for a page that is not in this document." }
          : turn));
        return;
      }
      setTurns((prev) => prev.map((turn) => turn.id === turnId
        ? { id: turnId, question: trimmed, status: result.data.status, result: result.data }
        : turn));
      return;
    }

    if (result.kind === "missing_index") {
      setTurns((prev) => prev.filter((turn) => turn.id !== turnId));
      setPreparation({ status: "error", kind: result.kind, message: result.message });
      return;
    }

    setTurns((prev) => prev.map((turn) => turn.id === turnId
      ? { id: turnId, question: trimmed, status: "error", message: result.message }
      : turn));
  }

  if (!eligible) return null;

  return (
    <section aria-labelledby="ask-doculens-heading" className="flex flex-col gap-4 rounded-card border border-zinc-200 bg-white p-5 shadow-sm">
      <div>
        <h2 id="ask-doculens-heading" className="text-lg font-semibold text-ink">Ask DocuLens</h2>
        <p className="mt-1 text-sm text-ink-muted">
          Ask a question or request analysis of this document — for example
          &ldquo;what is the termination deadline?&rdquo;, &ldquo;analyze the main
          risks&rdquo;, or &ldquo;summarize the obligations in section 3&rdquo;. Each
          answer is grounded in this document with page evidence, or reports that the
          document does not contain enough evidence to answer.
        </p>
      </div>

      {preparation.status !== "ready" ? (
        <div className="flex flex-col gap-3">
          {preparation.status === "preparing" ? (
            <p role="status" className="text-sm text-ink-muted">Preparing this document for Q&A…</p>
          ) : null}
          {preparation.status === "error" ? (
            <Reveal>
              <div className="flex flex-col gap-3">
                <p role="alert" className="text-sm font-medium text-red-700">{preparation.message}</p>
                {canRetryPreparation(preparation.kind) ? (
                  <button
                    type="button"
                    onClick={prepare}
                    className="inline-flex w-fit items-center justify-center rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent motion-safe:active:scale-[0.98]"
                  >
                    Retry preparation
                  </button>
                ) : null}
              </div>
            </Reveal>
          ) : null}
        </div>
      ) : (
        <>
          {turns.length ? (
            <StaggerGroup as="ul" className="flex flex-col gap-4" aria-label="Question and answer history">
              {turns.map((turn) => (
                <StaggerItem as="li" key={turn.id} className="list-none">
                  <AnswerTurn turn={turn} />
                </StaggerItem>
              ))}
            </StaggerGroup>
          ) : null}

          <form onSubmit={submit} aria-busy={answering} className="flex flex-col gap-3">
            <label htmlFor={questionId} className="text-sm font-medium text-ink-muted">Your question</label>
            <textarea id={questionId} value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={MAX_QUESTION_LENGTH} rows={3} placeholder="e.g. Analyze the termination risks and cite each conclusion." aria-describedby={questionError ? questionErrorId : undefined} className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent" />
            <p className="text-xs text-ink-subtle">{question.length}/{MAX_QUESTION_LENGTH} characters</p>
            {questionError ? <Reveal><p id={questionErrorId} role="alert" className="text-sm font-medium text-red-700">{questionError}</p></Reveal> : null}
            <button type="submit" disabled={answering || !question.trim()} className="inline-flex w-fit items-center justify-center rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50 motion-safe:active:scale-[0.98]">
              {answering ? "Asking DocuLens…" : "Ask DocuLens"}
            </button>
            <p aria-live="polite" className="sr-only">{answering ? "Asking DocuLens. Prior turns remain visible while a new answer is prepared." : ""}</p>
          </form>
        </>
      )}
    </section>
  );
}
