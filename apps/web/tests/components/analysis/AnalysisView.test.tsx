import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AnalysisView } from "@/components/analysis/AnalysisView";
import type { Analysis } from "@/lib/analysis-schema";

function baseAnalysis(overrides: Partial<Analysis> = {}): Analysis {
  return {
    id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    document_id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    document_type: "generic",
    extractor: "generic",
    status: "completed",
    summary: { title: null, purpose: "p", summary: "s", key_topics: [] },
    findings: [],
    important_dates: [],
    risks: [],
    specialized_analysis: null,
    provider: "openai",
    model: "gpt-4o-mini",
    created_at: "2026-08-29T12:34:56+00:00",
    ...overrides,
  } as Analysis;
}

describe("AnalysisView", () => {
  it("renders no specialized shell for a generic document", () => {
    render(<AnalysisView analysis={baseAnalysis()} />);

    expect(screen.queryByText("Parties")).not.toBeInTheDocument();
    expect(screen.queryByText("Functional requirements")).not.toBeInTheDocument();
    expect(screen.getByText("Key findings")).toBeInTheDocument();
  });

  it("renders only contract sections for a contract document", () => {
    render(
      <AnalysisView
        analysis={baseAnalysis({
          document_type: "contract",
          extractor: "contract_terms",
          specialized_analysis: {
            type: "contract",
            extractor: "contract_terms",
            parties: [],
            obligations: [],
            payment_terms: [],
            renewal_terms: [],
            termination_terms: [],
            liability_terms: [],
            confidentiality_terms: [],
          },
        })}
      />
    );

    expect(screen.getByRole("heading", { name: "Parties" })).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Functional requirements" })
    ).not.toBeInTheDocument();
  });

  it("renders only technical-specification sections for a technical specification", () => {
    render(
      <AnalysisView
        analysis={baseAnalysis({
          document_type: "technical_specification",
          extractor: "technical_specification_requirements",
          specialized_analysis: {
            type: "technical_specification",
            extractor: "technical_specification_requirements",
            functional_requirements: [],
            non_functional_requirements: [],
            security_requirements: [],
            integration_requirements: [],
            constraints: [],
            dependencies: [],
          },
        })}
      />
    );

    expect(
      screen.getByRole("heading", { name: "Functional requirements" })
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Parties" })).not.toBeInTheDocument();
  });
});
