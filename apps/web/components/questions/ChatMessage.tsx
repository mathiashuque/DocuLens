import { Reveal } from "@/components/motion/primitives";
import { EvidenceGroup } from "@/components/questions/EvidenceGroup";
import { ThinkingIndicator } from "@/components/questions/ThinkingIndicator";
import type { Turn } from "@/components/questions/types";

/** Small, code-native identity mark for an assistant message — no remote avatar. */
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

function UserBubble({ question }: { question: string }) {
  return (
    <div className="flex justify-end">
      <p className="max-w-[85%] min-w-0 rounded-card bg-accent px-4 py-2.5 text-sm break-words whitespace-pre-wrap text-white">
        <span className="sr-only">You asked: </span>
        {question}
      </p>
    </div>
  );
}

function AssistantRow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2.5">
      <AssistantMark />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

export function ChatMessage({ turn }: { turn: Turn }) {
  return (
    <div className="flex flex-col gap-3">
      <UserBubble question={turn.question} />

      {turn.status === "pending" ? (
        <AssistantRow>
          <ThinkingIndicator />
        </AssistantRow>
      ) : null}

      {turn.status === "error" ? (
        <Reveal>
          <AssistantRow>
            <p role="alert" className="rounded-card border border-red-300 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
              {turn.message}
            </p>
          </AssistantRow>
        </Reveal>
      ) : null}

      {turn.status === "insufficient_evidence" ? (
        <Reveal>
          <AssistantRow>
            <div className="rounded-card border border-amber-300 bg-amber-50 px-4 py-3" role="status">
              <p className="text-sm font-semibold text-amber-950">Insufficient evidence</p>
              <p className="mt-1 text-sm break-words whitespace-pre-wrap text-amber-900">{turn.result.answer}</p>
              <p className="mt-2 text-sm text-amber-900">Try rephrasing your question using terms from the document.</p>
            </div>
          </AssistantRow>
        </Reveal>
      ) : null}

      {turn.status === "answered" ? (
        <Reveal>
          <AssistantRow>
            <div className="max-w-full">
              <p className="text-[0.95rem] leading-7 break-words whitespace-pre-wrap text-ink">{turn.result.answer}</p>
              <EvidenceGroup citations={turn.result.citations} />
            </div>
          </AssistantRow>
        </Reveal>
      ) : null}
    </div>
  );
}
