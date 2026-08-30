import type { Risk } from "@/lib/analysis-schema";
import { ConfidenceLabel } from "./ConfidenceLabel";
import { EvidenceQuote } from "./EvidenceQuote";
import { LevelBadge } from "./LevelBadge";

export function RisksSection({ risks }: { risks: Risk[] }) {
  return (
    <section aria-labelledby="risks-heading" className="flex flex-col gap-4">
      <h2 id="risks-heading" className="text-lg font-semibold text-ink">
        Risks &amp; concerns
      </h2>

      {risks.length === 0 ? (
        <p className="text-sm text-ink-muted">
          No risks or concerns were identified in this document.
        </p>
      ) : (
        <ol className="flex flex-col gap-3">
          {risks.map((risk) => (
            <li key={risk.id} className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-ink">{risk.title}</h3>
                <LevelBadge level={risk.severity} label="Severity" />
              </div>
              <p className="mt-1 text-xs text-ink-subtle">{risk.category}</p>
              <p className="mt-2 text-sm text-ink-muted">{risk.description}</p>
              {risk.evidence.map((item, index) => (
                <EvidenceQuote key={index} page={item.page} quote={item.text} />
              ))}
              <div className="mt-2">
                <ConfidenceLabel confidence={risk.confidence} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
