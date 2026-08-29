import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FindingsSection } from "@/components/analysis/FindingsSection";

describe("FindingsSection", () => {
  it("shows an honest empty state when there are no findings", () => {
    render(<FindingsSection findings={[]} />);

    expect(
      screen.getByText("No notable findings were extracted from this document.")
    ).toBeInTheDocument();
  });

  it("renders a finding with its evidence quote, page link, confidence, and importance", () => {
    render(
      <FindingsSection
        findings={[
          {
            id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
            title: "Key point",
            description: "An important point.",
            category: "general",
            importance: "high",
            source_page: 3,
            evidence: "quoted evidence text",
            confidence: 0.82,
          },
        ]}
      />
    );

    expect(screen.getByText("Key point")).toBeInTheDocument();
    expect(screen.getByText("Importance: High")).toBeInTheDocument();
    expect(screen.getByText(/quoted evidence text/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View page 3" })).toHaveAttribute(
      "href",
      "#page-3"
    );
    expect(screen.getByText(/82% \(model estimate\)/)).toBeInTheDocument();
  });
});
