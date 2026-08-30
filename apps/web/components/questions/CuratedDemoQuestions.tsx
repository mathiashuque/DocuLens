"use client";

import { useState } from "react";

import { Reveal, StaggerGroup, StaggerItem } from "@/components/motion/primitives";
import { EvidenceGroup } from "@/components/questions/EvidenceGroup";
import type { Dictionary } from "@/lib/i18n/dictionary";
import type { Document } from "@/lib/document-schema";

type DemoQuestion = NonNullable<Document["demo_questions"]>[number];

function AssistantMark() {
  return (
    <span
      aria-hidden="true"
      className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-soft text-[10px] font-semibold text-accent-strong"
    >
      DL
    </span>
  );
}

/**
 * Curated demo answers rendered with the same message/evidence vocabulary as
 * live chat (compact right-aligned question, open left-aligned answer, the
 * same `EvidenceGroup`) — a safe precomputed variation of the real
 * experience, not a separate visual subsystem. The "Precomputed demo" notice
 * stays a compact badge rather than a large banner competing with the chat.
 */
export function CuratedDemoQuestions({
  questions,
  dict,
}: {
  questions: DemoQuestion[];
  dict: Dictionary["questions"];
}) {
  const [selected, setSelected] = useState<DemoQuestion | null>(null);

  return (
    <section aria-label={dict.demoQuestionsAriaLabel} className="flex flex-col gap-5 px-1 py-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-chip bg-sky-100 px-2.5 py-1 text-xs font-medium text-sky-900">
          <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-sky-500" />
          {dict.demoBadge}
        </span>
        <p className="text-xs text-ink-subtle">{dict.demoHint}</p>
      </div>

      <StaggerGroup as="ul" className="flex flex-wrap gap-2" aria-label={dict.demoExampleQuestionsAriaLabel}>
        {questions.map((item) => (
          <StaggerItem as="li" key={item.id} className="list-none">
            <button
              type="button"
              onClick={() => setSelected(item)}
              aria-pressed={selected?.id === item.id}
              className="rounded-chip border border-hairline bg-surface px-3.5 py-2 text-left text-sm text-ink-muted transition-colors hover:border-accent/40 hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent motion-safe:active:scale-[0.98]"
            >
              {item.question}
            </button>
          </StaggerItem>
        ))}
      </StaggerGroup>

      {selected ? (
        <Reveal>
          <div className="flex flex-col gap-3">
            <div className="ml-auto max-w-[85%] rounded-card bg-accent px-4 py-2.5 text-sm break-words whitespace-pre-wrap text-white">
              <span className="sr-only">{dict.exampleQuestionSr}</span>
              {selected.question}
            </div>
            <div className="flex items-start gap-2.5" role="status">
              <AssistantMark />
              <div className="min-w-0 flex-1">
                {selected.status === "insufficient_evidence" ? (
                  <div className="rounded-card border border-amber-300 bg-amber-50 px-4 py-3">
                    <p className="text-sm font-semibold text-amber-950">{dict.insufficientEvidenceTitle}</p>
                    <p className="mt-1 text-sm break-words whitespace-pre-wrap text-amber-900">{selected.answer}</p>
                  </div>
                ) : (
                  <div className="max-w-full">
                    <p className="text-[0.95rem] leading-7 break-words whitespace-pre-wrap text-ink">{selected.answer}</p>
                    <EvidenceGroup citations={selected.citations} dict={dict} />
                  </div>
                )}
              </div>
            </div>
          </div>
        </Reveal>
      ) : null}
    </section>
  );
}
