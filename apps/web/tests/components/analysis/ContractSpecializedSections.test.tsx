import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ContractSpecializedSections } from "@/components/analysis/ContractSpecializedSections";
import type { ContractAnalysis } from "@/lib/analysis-schema";

function emptyContract(overrides: Partial<ContractAnalysis> = {}): ContractAnalysis {
  return {
    type: "contract",
    extractor: "contract_terms",
    parties: [],
    obligations: [],
    payment_terms: [],
    renewal_terms: [],
    termination_terms: [],
    liability_terms: [],
    confidentiality_terms: [],
    ...overrides,
  };
}

describe("ContractSpecializedSections", () => {
  it("shows honest empty states for every category", () => {
    render(<ContractSpecializedSections contract={emptyContract()} />);

    expect(screen.getByText("No parties were identified.")).toBeInTheDocument();
    expect(screen.getByText("No obligations were identified.")).toBeInTheDocument();
    expect(screen.getByText("No payment terms were identified.")).toBeInTheDocument();
    expect(screen.getByText("No renewal clause was identified.")).toBeInTheDocument();
    expect(screen.getByText("No termination clause was identified.")).toBeInTheDocument();
    expect(screen.getByText("No liability clause was identified.")).toBeInTheDocument();
    expect(
      screen.getByText("No confidentiality clause was identified.")
    ).toBeInTheDocument();
  });

  it("renders a party with its role and evidence link", () => {
    render(
      <ContractSpecializedSections
        contract={emptyContract({
          parties: [
            {
              id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
              name: "Northstar Hosting Ltd.",
              role: "provider",
              source_page: 1,
              evidence: "Northstar Hosting Ltd. (Provider)",
              confidence: 0.97,
            },
          ],
        })}
      />
    );

    expect(screen.getByText("Northstar Hosting Ltd.")).toBeInTheDocument();
    expect(screen.getByText("Role: provider")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View page 1" })).toHaveAttribute(
      "href",
      "#page-1"
    );
  });

  it("preserves null obligated_party/beneficiary without fabricating a value", () => {
    render(
      <ContractSpecializedSections
        contract={emptyContract({
          obligations: [
            {
              id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
              obligated_party: null,
              description: "Maintain records",
              beneficiary: null,
              conditions: [],
              source_page: 2,
              evidence: "Records shall be maintained",
              confidence: 0.6,
            },
          ],
        })}
      />
    );

    expect(screen.getByText("Maintain records")).toBeInTheDocument();
    expect(screen.queryByText("Obligated party:")).not.toBeInTheDocument();
    expect(screen.queryByText("Beneficiary:")).not.toBeInTheDocument();
  });

  it("renders a renewal clause under its own heading, not termination", () => {
    render(
      <ContractSpecializedSections
        contract={emptyContract({
          renewal_terms: [
            {
              id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
              title: "Auto-renewal",
              description: "Renews automatically each year",
              conditions: [],
              notice_period_text: "30 days",
              source_page: 5,
              evidence: "renews automatically each year",
              confidence: 0.8,
            },
          ],
        })}
      />
    );

    expect(
      screen.getByRole("heading", { name: "Renewal" })
    ).toBeInTheDocument();
    expect(screen.getByText("Auto-renewal")).toBeInTheDocument();
    expect(screen.getByText("Notice period: 30 days")).toBeInTheDocument();
    expect(
      screen.getByText("No termination clause was identified.")
    ).toBeInTheDocument();
  });
});
