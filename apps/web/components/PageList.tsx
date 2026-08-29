import type { DocumentPage } from "@/lib/document-schema";
import { pageAnchorId } from "@/lib/analysis-evidence";

export function PageList({ pages }: { pages: DocumentPage[] }) {
  return (
    <section aria-labelledby="pages-heading" className="flex flex-col gap-4">
      <h2 id="pages-heading" className="text-lg font-semibold text-zinc-900">
        Pages
      </h2>

      <ol className="flex flex-col gap-4">
        {pages.map((page) => (
          <li
            key={page.page_number}
            id={pageAnchorId(page.page_number)}
            className="scroll-mt-6 rounded-md border border-zinc-200 bg-white p-4"
          >
            <h3 className="text-sm font-semibold text-zinc-900">
              Page {page.page_number}
            </h3>
            <p className="mt-2 whitespace-pre-wrap break-words text-sm text-zinc-700">
              {page.text ? page.text : "No text extracted from this page."}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
