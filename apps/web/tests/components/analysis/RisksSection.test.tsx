import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RisksSection } from "@/components/analysis/RisksSection";

describe("RisksSection", () => {
  it("shows an honest empty state when there are no risks", () => {
    render(<RisksSection risks={[]} />);

    expect(
      screen.getByText("No risks or concerns were identified in this document.")
    ).toBeInTheDocument();
  });

  it("renders each page/quote pair of a multi-page risk separately", () => {
    render(
      <RisksSection
        risks={[
          {
            id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
            title: "Auto-renewal risk",
            description: "d",
            category: "renewal",
            severity: "critical",
            evidence: [
              { page: 1, text: "renews automatically" },
              { page: 4, text: "60 days notice required" },
            ],
            confidence: 0.6,
          },
        ]}
      />
    );

    expect(screen.getByText("Severity: Critical")).toBeInTheDocument();
    expect(screen.getByText(/renews automatically/)).toBeInTheDocument();
    expect(screen.getByText(/60 days notice required/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View page 1" })).toHaveAttribute(
      "href",
      "#page-1"
    );
    expect(screen.getByRole("link", { name: "View page 4" })).toHaveAttribute(
      "href",
      "#page-4"
    );
  });
});
