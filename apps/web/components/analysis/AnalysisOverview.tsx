import type { AnalysisSummary, DocumentType, Extractor } from "@/lib/analysis-schema";
import { formatDateTime } from "@/lib/format";

const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  contract: "Contract",
  technical_specification: "Technical specification",
  generic: "Document",
};

export function AnalysisOverview({
  documentType,
  extractor,
  summary,
  createdAt,
}: {
  documentType: DocumentType;
  extractor: Extractor;
  summary: AnalysisSummary;
  createdAt: string;
}) {
  return (
    <div className="flex flex-col gap-4 rounded-card border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="inline-flex items-center rounded-chip bg-accent px-2.5 py-1 text-xs font-medium text-white">
          {DOCUMENT_TYPE_LABELS[documentType]} analysis
        </span>
        <span className="text-xs text-ink-subtle">
          AI-generated &middot; analyzed {formatDateTime(createdAt)}
        </span>
      </div>

      {summary.title ? (
        <h3 className="text-base font-semibold text-ink">{summary.title}</h3>
      ) : null}

      <p className="text-sm text-ink-muted">{summary.purpose}</p>
      <p className="text-sm text-ink-muted">{summary.summary}</p>

      {summary.key_topics.length > 0 ? (
        <ul className="flex flex-wrap gap-2" aria-label="Key topics">
          {summary.key_topics.map((topic) => (
            <li
              key={topic}
              className="rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-ink-muted"
            >
              {topic}
            </li>
          ))}
        </ul>
      ) : null}

      <p className="text-xs text-zinc-400">Extractor: {extractor}</p>
    </div>
  );
}
