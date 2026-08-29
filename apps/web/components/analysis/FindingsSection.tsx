import type { Finding } from "@/lib/analysis-schema";
import { ConfidenceLabel } from "./ConfidenceLabel";
import { EvidenceQuote } from "./EvidenceQuote";
import { LevelBadge } from "./LevelBadge";

export function FindingsSection({ findings }: { findings: Finding[] }) {
  return (
    <section aria-labelledby="findings-heading" className="flex flex-col gap-4">
      <h2 id="findings-heading" className="text-lg font-semibold text-zinc-900">
        Key findings
      </h2>

      {findings.length === 0 ? (
        <p className="text-sm text-zinc-600">
          No notable findings were extracted from this document.
        </p>
      ) : (
        <ol className="flex flex-col gap-3">
          {findings.map((finding) => (
            <li
              key={finding.id}
              className="rounded-md border border-zinc-200 bg-white p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-zinc-900">{finding.title}</h3>
                <LevelBadge level={finding.importance} label="Importance" />
              </div>
              <p className="mt-1 text-xs text-zinc-500">{finding.category}</p>
              <p className="mt-2 text-sm text-zinc-700">{finding.description}</p>
              <EvidenceQuote page={finding.source_page} quote={finding.evidence} />
              <div className="mt-2">
                <ConfidenceLabel confidence={finding.confidence} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
