import { pageAnchorId } from "@/lib/analysis-evidence";

/**
 * Renders one evidence page/quote pair with a visible quote (never hidden
 * exclusively behind hover) and a keyboard-accessible link to the physical
 * page's in-page anchor. Callers must only pass pages already confirmed to
 * exist on the loaded document (see `analysisPagesExistIn`).
 */
export function EvidenceQuote({ page, quote }: { page: number; quote: string }) {
  return (
    <figure className="mt-2 rounded-md border border-zinc-200 bg-zinc-50 p-3">
      <blockquote className="whitespace-pre-wrap break-words text-sm text-zinc-700">
        &ldquo;{quote}&rdquo;
      </blockquote>
      <figcaption className="mt-2 text-xs text-zinc-500">
        <a
          href={`#${pageAnchorId(page)}`}
          className="font-medium text-zinc-700 underline underline-offset-2 hover:text-zinc-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
        >
          View page {page}
        </a>
      </figcaption>
    </figure>
  );
}
