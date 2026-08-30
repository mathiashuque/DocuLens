import { StaggerGroup, StaggerItem } from "@/components/motion/primitives";

const EXAMPLES = [
  "Summarize this document",
  "Identify the main risks",
  "List important deadlines",
  "What should I pay attention to?",
] as const;

/**
 * Empty-state example prompts. Clicking one only populates and focuses the
 * composer — it never submits a paid question on its own, so no click here
 * spends allowance without an explicit, separate send action.
 */
export function ExamplePrompts({ onSelect }: { onSelect: (prompt: string) => void }) {
  return (
    <StaggerGroup as="ul" className="flex flex-wrap justify-center gap-2" aria-label="Example prompts">
      {EXAMPLES.map((prompt) => (
        <StaggerItem as="li" key={prompt} className="list-none">
          <button
            type="button"
            onClick={() => onSelect(prompt)}
            className="rounded-chip border border-hairline bg-surface px-3.5 py-2 text-sm text-ink-muted transition-colors hover:border-accent/40 hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent motion-safe:active:scale-[0.98]"
          >
            {prompt}
          </button>
        </StaggerItem>
      ))}
    </StaggerGroup>
  );
}
