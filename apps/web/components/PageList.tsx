import type { DocumentPage } from "@/lib/document-schema";
import { pageAnchorId } from "@/lib/analysis-evidence";

/**
 * Deliberately unanimated: a document can have hundreds of pages, and
 * staggering that many mount transitions would both feel slow and defeat
 * the point of restrained motion.
 */
export function PageList({ pages }: { pages: DocumentPage[] }) {
  return (
    <section aria-labelledby="pages-heading" className="flex flex-col gap-4">
      <h2 id="pages-heading" className="text-lg font-semibold text-ink">
        Pages
      </h2>

      <ol className="flex flex-col gap-4">
        {pages.map((page) => (
          <li
            key={page.page_number}
            id={pageAnchorId(page.page_number)}
            className="scroll-mt-20 rounded-lg border border-zinc-200 bg-white p-4 shadow-sm"
          >
            <h3 className="text-sm font-semibold text-ink">
              Page {page.page_number}
            </h3>
            <p className="mt-2 whitespace-pre-wrap break-words text-sm text-ink-muted">
              {page.text ? page.text : "No text extracted from this page."}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
