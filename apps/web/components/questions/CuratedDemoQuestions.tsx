"use client";

import { useState } from "react";

import { EvidenceQuote } from "@/components/analysis/EvidenceQuote";
import type { Document } from "@/lib/document-schema";

type DemoQuestion = NonNullable<Document["demo_questions"]>[number];

export function CuratedDemoQuestions({ questions }: { questions: DemoQuestion[] }) {
  const [selected, setSelected] = useState<DemoQuestion | null>(null);
  return (
    <section aria-labelledby="demo-questions-heading" className="flex flex-col gap-4 rounded-md border border-sky-200 bg-sky-50 p-5">
      <div>
        <h2 id="demo-questions-heading" className="text-lg font-semibold text-zinc-900">Precomputed questions</h2>
        <p className="mt-1 text-sm text-zinc-700">Choose an example question. These answers are curated and do not call an AI provider.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {questions.map((item) => <button key={item.id} type="button" onClick={() => setSelected(item)} className="rounded-md border border-sky-300 bg-white px-3 py-2 text-left text-sm font-medium text-zinc-800 focus-visible:outline focus-visible:outline-2">{item.question}</button>)}
      </div>
      {selected ? (
        <div className="rounded-md border border-zinc-200 bg-white p-4" role="status">
          <h3 className="font-semibold text-zinc-900">{selected.status === "answered" ? "Answer" : "Insufficient evidence"}</h3>
          <p className="mt-2 whitespace-pre-wrap break-words text-sm text-zinc-700">{selected.answer}</p>
          {selected.citations.length ? <ol aria-label="Answer citations" className="mt-3 flex flex-col gap-3">{selected.citations.map((citation, index) => <li key={citation.chunk_id}><p className="text-sm font-medium">Citation {index + 1}: Page {citation.page}</p><EvidenceQuote page={citation.page} quote={citation.evidence} /></li>)}</ol> : null}
        </div>
      ) : null}
    </section>
  );
}
