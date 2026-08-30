import { StaggerGroup, StaggerItem } from "@/components/motion/primitives";
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
 * (or none at all for a generic document — no empty specialized shell). The
 * stagger here is over this small, fixed set of *sections*, not over the
 * findings/risks/dates inside them — those lists are left unanimated.
 */
export function AnalysisView({ analysis }: { analysis: Analysis }) {
  return (
    <StaggerGroup className="flex flex-col gap-8">
      <StaggerItem>
        <AnalysisOverview
          documentType={analysis.document_type}
          extractor={analysis.extractor}
          summary={analysis.summary}
          createdAt={analysis.created_at}
        />
      </StaggerItem>
      <StaggerItem>
        <FindingsSection findings={analysis.findings} />
      </StaggerItem>
      <StaggerItem>
        <ImportantDatesSection dates={analysis.important_dates} />
      </StaggerItem>
      <StaggerItem>
        <RisksSection risks={analysis.risks} />
      </StaggerItem>
      {analysis.specialized_analysis?.type === "contract" ? (
        <StaggerItem>
          <ContractSpecializedSections contract={analysis.specialized_analysis} />
        </StaggerItem>
      ) : null}
      {analysis.specialized_analysis?.type === "technical_specification" ? (
        <StaggerItem>
          <TechnicalSpecSpecializedSections spec={analysis.specialized_analysis} />
        </StaggerItem>
      ) : null}
    </StaggerGroup>
  );
}
