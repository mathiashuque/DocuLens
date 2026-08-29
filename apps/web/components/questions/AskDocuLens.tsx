"use client";

import { useId, useState } from "react";

import { EvidenceQuote } from "@/components/analysis/EvidenceQuote";
import {
  askDocumentQuestion,
  prepareQuestionAnswering,
  type QuestionFailureKind,
} from "@/lib/question-actions";
import { MAX_QUESTION_LENGTH, type QuestionResponse } from "@/lib/question-schema";
import type { DocumentStatus } from "@/lib/document-schema";

type PreparationState =
  | { status: "not_prepared" }
  | { status: "preparing" }
  | { status: "ready" }
  | { status: "error"; kind: QuestionFailureKind; message: string };

function canRetryPreparation(kind: QuestionFailureKind) {
  return kind !== "ineligible_document" && kind !== "incompatible_index" && kind !== "not_found";
}

function AnswerResult({ result }: { result: QuestionResponse }) {
  if (result.status === "insufficient_evidence") {
    return (
      <div className="rounded-md border border-amber-300 bg-amber-50 p-4" role="status">
        <h3 className="font-semibold text-amber-950">Insufficient evidence</h3>
        <p className="mt-1 whitespace-pre-wrap break-words text-sm text-amber-900">{result.answer}</p>
        <p className="mt-2 text-sm text-amber-900">Try rephrasing your question using terms from the document.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 rounded-md border border-zinc-200 bg-zinc-50 p-4">
      <div>
        <h3 className="font-semibold text-zinc-900">Answer</h3>
        <p className="mt-1 whitespace-pre-wrap break-words text-sm text-zinc-700">{result.answer}</p>
      </div>
      <ol className="flex flex-col gap-3" aria-label="Answer citations">
        {result.citations.map((citation, index) => (
          <li key={citation.chunk_id}>
            <p className="text-sm font-medium text-zinc-800">Citation {index + 1}: Page {citation.page}</p>
            <EvidenceQuote page={citation.page} quote={citation.evidence} />
          </li>
        ))}
      </ol>
    </div>
  );
}

/** A single-document, explicit-cost Q&A interaction; it intentionally has no history. */
export function AskDocuLens({
  documentId,
  documentStatus,
  documentPageNumbers,
}: {
  documentId: string;
  documentStatus: DocumentStatus;
  documentPageNumbers: readonly number[];
}) {
  const [preparation, setPreparation] = useState<PreparationState>({ status: "not_prepared" });
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<QuestionResponse | null>(null);
  const [answering, setAnswering] = useState(false);
  const [questionError, setQuestionError] = useState<string | null>(null);
  const questionId = useId();
  const questionErrorId = useId();
  const eligible = documentStatus === "parsed";

  async function prepare() {
    if (preparation.status === "preparing") return;
    setPreparation({ status: "preparing" });
    const result = await prepareQuestionAnswering(documentId);
    setPreparation(result.ok ? { status: "ready" } : { status: "error", kind: result.kind, message: result.message });
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (answering || !question.trim()) {
      if (!question.trim()) setQuestionError("Enter a question before asking DocuLens.");
      return;
    }
    setAnswering(true);
    setQuestionError(null);
    const result = await askDocumentQuestion(documentId, question);
    setAnswering(false);
    if (result.ok) {
      if (!result.data.citations.every((citation) => documentPageNumbers.includes(citation.page))) {
        setQuestionError("The Q&A service returned a citation for a page that is not in this document.");
        return;
      }
      setAnswer(result.data);
      return;
    }
    if (result.kind === "missing_index") {
      setPreparation({ status: "error", kind: result.kind, message: result.message });
      return;
    }
    setQuestionError(result.message);
  }

  if (!eligible) return null;

  return (
    <section aria-labelledby="ask-doculens-heading" className="flex flex-col gap-4 rounded-md border border-zinc-200 bg-white p-5">
      <div>
        <h2 id="ask-doculens-heading" className="text-lg font-semibold text-zinc-900">Ask DocuLens</h2>
        <p className="mt-1 text-sm text-zinc-600">Ask one question at a time. Answers are grounded in this document and include page evidence.</p>
      </div>

      {preparation.status !== "ready" ? (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-zinc-700">Prepare this document for Q&A before asking a question.</p>
          {preparation.status === "error" ? <p role="alert" className="text-sm font-medium text-red-700">{preparation.message}</p> : null}
          {preparation.status !== "error" || canRetryPreparation(preparation.kind) ? (
            <button type="button" onClick={prepare} disabled={preparation.status === "preparing"} className="inline-flex w-fit items-center justify-center rounded-md bg-zinc-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-zinc-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900 disabled:cursor-not-allowed disabled:opacity-50">
              {preparation.status === "preparing" ? "Preparing Q&A…" : "Prepare Q&A"}
            </button>
          ) : null}
          <p aria-live="polite" className="sr-only">{preparation.status === "preparing" ? "Preparing Q&A for this document." : ""}</p>
        </div>
      ) : (
        <form onSubmit={submit} aria-busy={answering} className="flex flex-col gap-3">
          <label htmlFor={questionId} className="text-sm font-medium text-zinc-800">Your question</label>
          <textarea id={questionId} value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={MAX_QUESTION_LENGTH} rows={3} aria-describedby={questionError ? questionErrorId : undefined} className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm text-zinc-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900" />
          <p className="text-xs text-zinc-500">{question.length}/{MAX_QUESTION_LENGTH} characters</p>
          {questionError ? <p id={questionErrorId} role="alert" className="text-sm font-medium text-red-700">{questionError}</p> : null}
          <button type="submit" disabled={answering || !question.trim()} className="inline-flex w-fit items-center justify-center rounded-md bg-zinc-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-zinc-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900 disabled:cursor-not-allowed disabled:opacity-50">
            {answering ? "Asking DocuLens…" : "Ask DocuLens"}
          </button>
          <p aria-live="polite" className="sr-only">{answering ? "Asking DocuLens. The current answer remains visible while a new answer is prepared." : ""}</p>
        </form>
      )}
      {answer ? <AnswerResult result={answer} /> : null}
    </section>
  );
}
