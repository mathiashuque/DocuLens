import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TechnicalSpecSpecializedSections } from "@/components/analysis/TechnicalSpecSpecializedSections";
import type { TechnicalSpecAnalysis } from "@/lib/analysis-schema";

function emptySpec(
  overrides: Partial<TechnicalSpecAnalysis> = {}
): TechnicalSpecAnalysis {
  return {
    type: "technical_specification",
    extractor: "technical_specification_requirements",
    functional_requirements: [],
    non_functional_requirements: [],
    security_requirements: [],
    integration_requirements: [],
    constraints: [],
    dependencies: [],
    ...overrides,
  };
}

describe("TechnicalSpecSpecializedSections", () => {
  it("shows honest empty states for every category", () => {
    render(<TechnicalSpecSpecializedSections spec={emptySpec()} />);

    expect(
      screen.getByText("No functional requirements were identified.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("No non-functional requirements were identified.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("No security requirements were identified.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("No integration requirements were identified.")
    ).toBeInTheDocument();
    expect(screen.getByText("No constraints were identified.")).toBeInTheDocument();
    expect(screen.getByText("No dependencies were identified.")).toBeInTheDocument();
  });

  it("renders a functional requirement with its source ID, priority, and actor", () => {
    render(
      <TechnicalSpecSpecializedSections
        spec={emptySpec({
          functional_requirements: [
            {
              id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
              identifier: "FR-12",
              statement: "The service shall allow administrators to revoke active sessions.",
              priority: "must",
              actor: "administrator",
              measurable_criterion: null,
              source_page: 8,
              evidence: "FR-12: The service shall allow administrators to revoke active sessions.",
              confidence: 0.98,
            },
          ],
        })}
      />
    );

    expect(
      screen.getByRole("heading", { level: 3, name: /FR-12:/ })
    ).toBeInTheDocument();
    expect(screen.getByText("Priority: Must")).toBeInTheDocument();
    expect(screen.getByText("administrator")).toBeInTheDocument();
  });

  it("omits the source ID prefix when absent, without fabricating one", () => {
    render(
      <TechnicalSpecSpecializedSections
        spec={emptySpec({
          functional_requirements: [
            {
              id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
              identifier: null,
              statement: "Export data as CSV",
              priority: "unspecified",
              actor: null,
              measurable_criterion: null,
              source_page: 2,
              evidence: "shall let users export their data as a CSV file",
              confidence: 0.7,
            },
          ],
        })}
      />
    );

    expect(screen.getByText("Export data as CSV")).toBeInTheDocument();
    expect(screen.getByText("Priority: Unspecified")).toBeInTheDocument();
  });

  it("renders a constraint's category and raw value", () => {
    render(
      <TechnicalSpecSpecializedSections
        spec={emptySpec({
          constraints: [
            {
              id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
              category: "performance",
              statement: "Response time limit",
              value_text: "under 200ms p95",
              source_page: 3,
              evidence: "Response time shall not exceed 200ms p95",
              confidence: 0.8,
            },
          ],
        })}
      />
    );

    expect(screen.getByText("Performance")).toBeInTheDocument();
    expect(screen.getByText("Value: under 200ms p95")).toBeInTheDocument();
  });

  it("renders a dependency's name, type, and description", () => {
    render(
      <TechnicalSpecSpecializedSections
        spec={emptySpec({
          dependencies: [
            {
              id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
              name: "Payment Gateway API",
              dependency_type: "external service",
              description: "Integrates with the external payment gateway",
              source_page: 5,
              evidence: "The system depends on the Payment Gateway API for billing",
              confidence: 0.7,
            },
          ],
        })}
      />
    );

    expect(screen.getByText("Payment Gateway API")).toBeInTheDocument();
    expect(screen.getByText("external service")).toBeInTheDocument();
  });
});
