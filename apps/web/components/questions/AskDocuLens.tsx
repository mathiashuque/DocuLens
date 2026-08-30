"use client";

import { useEffect, useRef, useState } from "react";

import { Reveal, useReducedMotionSafe } from "@/components/motion/primitives";
import { ChatMessage } from "@/components/questions/ChatMessage";
import { Composer } from "@/components/questions/Composer";
import { ExamplePrompts } from "@/components/questions/ExamplePrompts";
import type { Turn } from "@/components/questions/types";
import {
  askDocumentQuestion,
  prepareQuestionAnswering,
  type QuestionFailureKind,
} from "@/lib/question-actions";
import { MAX_QUESTION_LENGTH } from "@/lib/question-schema";
import type { DocumentStatus } from "@/lib/document-schema";

type PreparationState =
  | { status: "preparing" }
  | { status: "ready" }
  | { status: "error"; kind: QuestionFailureKind; message: string };

const NEAR_BOTTOM_THRESHOLD_PX = 96;

function canRetryPreparation(kind: QuestionFailureKind) {
  return kind !== "ineligible_document" && kind !== "incompatible_index" && kind !== "not_found";
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
  const [showJumpToLatest, setShowJumpToLatest] = useState(false);
  const preparingRef = useRef(false);
  const isNearBottomRef = useRef(true);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const nextTurnIdRef = useRef(0);
  const reduceMotion = useReducedMotionSafe();
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

  useEffect(() => {
    if (!turns.length) return;
    if (isNearBottomRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "end" });
      setShowJumpToLatest(false);
    } else {
      setShowJumpToLatest(true);
    }
  }, [turns.length, reduceMotion]);

  function handleTranscriptScroll() {
    const el = transcriptRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_THRESHOLD_PX;
    isNearBottomRef.current = nearBottom;
    if (nearBottom) setShowJumpToLatest(false);
  }

  function jumpToLatest() {
    isNearBottomRef.current = true;
    setShowJumpToLatest(false);
    bottomRef.current?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "end" });
  }

  function submit() {
    const trimmed = question.trim();
    if (answering || !trimmed) {
      if (!trimmed) setQuestionError("Enter a question before asking DocuLens.");
      return;
    }
    setQuestionError(null);
    nextTurnIdRef.current += 1;
    const turnId = `turn-${nextTurnIdRef.current}`;
    setTurns((prev) => [...prev, { id: turnId, question: trimmed, status: "pending" }]);
    setQuestion("");
    void resolveTurn(turnId, trimmed);
  }

  async function resolveTurn(turnId: string, trimmed: string) {
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
    <section aria-label="Ask DocuLens" className="flex min-h-0 flex-1 flex-col">
      {preparation.status !== "ready" ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 px-4 text-center">
          {preparation.status === "preparing" ? (
            <p role="status" className="text-sm text-ink-muted">Preparing this document for Q&amp;A…</p>
          ) : null}
          {preparation.status === "error" ? (
            <Reveal>
              <div className="flex flex-col items-center gap-3">
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
          <div
            ref={transcriptRef}
            onScroll={handleTranscriptScroll}
            role="log"
            aria-label="Conversation with DocuLens"
            className="relative flex-1 min-h-0 overflow-y-auto"
          >
            {turns.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center gap-6 px-4 py-10 text-center">
                <div>
                  <h2 className="text-xl font-semibold text-ink">What would you like to know?</h2>
                  <p className="mt-1.5 text-sm text-ink-muted">
                    Answers are grounded in this document, with page evidence or an
                    honest insufficient-evidence result.
                  </p>
                </div>
                <ExamplePrompts onSelect={setQuestion} />
              </div>
            ) : (
              <ol className="flex flex-col gap-6 px-1 py-4">
                {turns.map((turn) => (
                  <li key={turn.id}>
                    <ChatMessage turn={turn} />
                  </li>
                ))}
              </ol>
            )}
            <div ref={bottomRef} />
          </div>

          {showJumpToLatest ? (
            <div className="flex justify-center pb-2">
              <button
                type="button"
                onClick={jumpToLatest}
                className="rounded-chip border border-hairline bg-surface px-3 py-1.5 text-xs font-medium text-ink-muted shadow-card hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Jump to latest ↓
              </button>
            </div>
          ) : null}

          <div className="shrink-0 pt-2">
            <Composer
              value={question}
              onChange={setQuestion}
              onSubmit={submit}
              disabled={answering}
              maxLength={MAX_QUESTION_LENGTH}
              error={questionError}
            />
          </div>
        </>
      )}
    </section>
  );
}
