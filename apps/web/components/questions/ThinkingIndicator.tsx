import type { Dictionary } from "@/lib/i18n/dictionary";

/**
 * Three softly sequenced dots indicating a pending answer. Pure CSS
 * (`animate-pulse` with staggered delays) so it respects the existing global
 * `prefers-reduced-motion` safety net in `globals.css` without a Motion
 * dependency — under reduced motion the animation duration collapses and the
 * dots simply render static, never blocking or delaying the status text.
 */
export function ThinkingIndicator({ dict }: { dict: Dictionary["questions"] }) {
  return (
    <div className="flex items-center gap-2 rounded-card bg-surface-muted px-4 py-3" role="status">
      <span className="flex items-center gap-1" aria-hidden="true">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink-subtle [animation-delay:0ms]" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink-subtle [animation-delay:150ms]" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink-subtle [animation-delay:300ms]" />
      </span>
      <span className="sr-only">{dict.thinkingSr}</span>
    </div>
  );
}
