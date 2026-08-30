import type { ImportantDate } from "@/lib/analysis-schema";
import { ConfidenceLabel } from "./ConfidenceLabel";
import { EvidenceQuote } from "./EvidenceQuote";

export function ImportantDatesSection({ dates }: { dates: ImportantDate[] }) {
  return (
    <section aria-labelledby="important-dates-heading" className="flex flex-col gap-4">
      <h2 id="important-dates-heading" className="text-lg font-semibold text-ink">
        Important dates
      </h2>

      {dates.length === 0 ? (
        <p className="text-sm text-ink-muted">
          No important dates were extracted from this document.
        </p>
      ) : (
        <ol className="flex flex-col gap-3">
          {dates.map((date) => (
            <li
              key={date.id}
              className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm"
            >
              <h3 className="text-sm font-semibold text-ink">{date.label}</h3>
              <dl className="mt-1 flex flex-wrap gap-x-6 gap-y-1 text-xs text-ink-muted">
                <div>
                  <dt className="inline font-medium text-ink">As written: </dt>
                  <dd className="inline">{date.raw_value}</dd>
                </div>
                {date.normalized_date ? (
                  <div>
                    <dt className="inline font-medium text-ink">Normalized: </dt>
                    <dd className="inline">{date.normalized_date}</dd>
                  </div>
                ) : null}
              </dl>
              <EvidenceQuote page={date.source_page} quote={date.evidence} />
              <div className="mt-2">
                <ConfidenceLabel confidence={date.confidence} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
