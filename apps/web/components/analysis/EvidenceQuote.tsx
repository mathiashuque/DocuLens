import { interpolate } from "@/lib/i18n/interpolate";

/**
 * Renders one evidence page/quote pair with a visible quote (never hidden
 * exclusively behind hover). The chat route no longer renders raw pages, so
 * this shows the physical page number as plain text rather than a jump link
 * to a page anchor that no longer exists.
 */
export function EvidenceQuote({
  page,
  quote,
  pageLabel,
}: {
  page: number;
  quote: string;
  pageLabel: string;
}) {
  return (
    <figure className="mt-2 rounded-md border-y border-r border-l-2 border-hairline border-l-accent bg-accent-soft/40 py-2 pr-3 pl-3">
      <blockquote className="whitespace-pre-wrap break-words text-sm text-ink-muted italic">
        &ldquo;{quote}&rdquo;
      </blockquote>
      <figcaption className="mt-2 text-xs font-medium text-ink-subtle not-italic">
        {interpolate(pageLabel, { page })}
      </figcaption>
    </figure>
  );
}
