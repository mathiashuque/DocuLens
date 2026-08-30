import { pageAnchorId } from "@/lib/analysis-evidence";

/**
 * Renders one evidence page/quote pair with a visible quote (never hidden
 * exclusively behind hover) and a keyboard-accessible link to the physical
 * page's in-page anchor. Callers must only pass pages already confirmed to
 * exist on the loaded document (see `analysisPagesExistIn`).
 */
export function EvidenceQuote({ page, quote }: { page: number; quote: string }) {
  return (
    <figure className="mt-2 rounded-md border-y border-r border-l-2 border-zinc-200 border-l-accent bg-accent-soft/40 py-2 pr-3 pl-3">
      <blockquote className="whitespace-pre-wrap break-words text-sm text-ink-muted italic">
        &ldquo;{quote}&rdquo;
      </blockquote>
      <figcaption className="mt-2 text-xs text-ink-subtle not-italic">
        <a
          href={`#${pageAnchorId(page)}`}
          className="font-medium text-accent-strong underline underline-offset-2 hover:text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          View page {page}
        </a>
      </figcaption>
    </figure>
  );
}
