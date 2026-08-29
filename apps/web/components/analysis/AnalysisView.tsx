import type { Analysis } from "@/lib/analysis-schema";
import { AnalysisOverview } from "./AnalysisOverview";
import { ContractSpecializedSections } from "./ContractSpecializedSections";
import { FindingsSection } from "./FindingsSection";
import { ImportantDatesSection } from "./ImportantDatesSection";
import { RisksSection } from "./RisksSection";
import { TechnicalSpecSpecializedSections } from "./TechnicalSpecSpecializedSections";

/**
 * Composes the full completed-analysis view: the shared overview/findings/
 * dates/risks sections every document type gets, plus the specialized
 * sections for whichever discriminated type `specialized_analysis` carries
 * (or none at all for a generic document — no empty specialized shell).
 */
export function AnalysisView({ analysis }: { analysis: Analysis }) {
  return (
    <div className="flex flex-col gap-8">
      <AnalysisOverview
        documentType={analysis.document_type}
        extractor={analysis.extractor}
        summary={analysis.summary}
        createdAt={analysis.created_at}
      />
      <FindingsSection findings={analysis.findings} />
      <ImportantDatesSection dates={analysis.important_dates} />
      <RisksSection risks={analysis.risks} />
      {analysis.specialized_analysis?.type === "contract" ? (
        <ContractSpecializedSections contract={analysis.specialized_analysis} />
      ) : null}
      {analysis.specialized_analysis?.type === "technical_specification" ? (
        <TechnicalSpecSpecializedSections spec={analysis.specialized_analysis} />
      ) : null}
    </div>
  );
}
