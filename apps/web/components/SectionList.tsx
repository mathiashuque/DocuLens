import type { DocumentSection } from "@/lib/document-schema";
import { formatPageRange } from "@/lib/format";

export function SectionList({ sections }: { sections: DocumentSection[] }) {
  return (
    <section aria-labelledby="document-structure-heading" className="flex flex-col gap-4">
      <h2 id="document-structure-heading" className="text-lg font-semibold text-ink">
        Document structure
      </h2>

      {sections.length === 0 ? (
        <p className="text-sm text-ink-muted">
          No reliable headings were detected in this document. Page-by-page text
          remains available below.
        </p>
      ) : (
        <ol className="flex flex-col gap-3">
          {sections.map((section) => (
            <li
              key={section.id}
              style={{ marginLeft: `${(section.level - 1) * 1.25}rem` }}
              className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm"
            >
              <p className="truncate text-xs text-ink-subtle">
                {section.section_path.join(" › ")}
              </p>
              <h3 className="mt-1 break-words text-sm font-semibold text-ink">
                {section.title}
              </h3>
              <p className="mt-1 text-xs text-ink-muted">
                {formatPageRange(section.page_start, section.page_end)}
              </p>
              {section.text ? (
                <details className="mt-2">
                  <summary className="cursor-pointer text-xs font-medium text-ink-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
                    Show section text
                  </summary>
                  <p className="mt-2 whitespace-pre-wrap break-words text-sm text-ink-muted">
                    {section.text}
                  </p>
                </details>
              ) : null}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
