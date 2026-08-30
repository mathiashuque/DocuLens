import { EvidenceQuote } from "@/components/analysis/EvidenceQuote";
import { StaggerGroup, StaggerItem } from "@/components/motion/primitives";
import type { QuestionCitation } from "@/lib/question-schema";

/**
 * Always-visible "Sources" region grouping an answer's citations. Kept
 * non-collapsible: evidence is a product invariant, not decorative metadata,
 * and an always-expanded list keeps it discoverable without adding a
 * disclosure control (and its own accessible-state tests) that this scope
 * does not need.
 */
export function EvidenceGroup({ citations }: { citations: readonly QuestionCitation[] }) {
  if (!citations.length) return null;

  return (
    <div className="mt-3 flex flex-col gap-2 border-t border-hairline pt-3">
      <p className="text-xs font-semibold tracking-wide text-ink-subtle uppercase">
        Sources
      </p>
      <StaggerGroup as="ul" className="flex flex-col gap-3" aria-label="Answer citations">
        {citations.map((citation, index) => (
          <StaggerItem as="li" key={citation.chunk_id} className="list-none">
            <p className="text-xs font-medium text-ink-subtle">Citation {index + 1}</p>
            <EvidenceQuote page={citation.page} quote={citation.evidence} />
          </StaggerItem>
        ))}
      </StaggerGroup>
    </div>
  );
}
