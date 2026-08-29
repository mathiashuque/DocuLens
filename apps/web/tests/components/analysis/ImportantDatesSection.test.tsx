import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ImportantDatesSection } from "@/components/analysis/ImportantDatesSection";

describe("ImportantDatesSection", () => {
  it("shows an honest empty state when there are no dates", () => {
    render(<ImportantDatesSection dates={[]} />);

    expect(
      screen.getByText("No important dates were extracted from this document.")
    ).toBeInTheDocument();
  });

  it("renders both the raw and normalized date when present", () => {
    render(
      <ImportantDatesSection
        dates={[
          {
            id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
            label: "Renewal",
            raw_value: "March 3, 2027",
            normalized_date: "2027-03-03",
            source_page: 2,
            evidence: "next review is scheduled for March 3, 2027",
            confidence: 0.5,
          },
        ]}
      />
    );

    expect(screen.getByText("March 3, 2027")).toBeInTheDocument();
    expect(screen.getByText("2027-03-03")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View page 2" })).toHaveAttribute(
      "href",
      "#page-2"
    );
  });

  it("omits the normalized date row when uncertain", () => {
    render(
      <ImportantDatesSection
        dates={[
          {
            id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
            label: "Renewal",
            raw_value: "next spring",
            normalized_date: null,
            source_page: 1,
            evidence: "renews next spring",
            confidence: 0.4,
          },
        ]}
      />
    );

    expect(screen.getByText("next spring")).toBeInTheDocument();
    expect(screen.queryByText("Normalized:")).not.toBeInTheDocument();
  });
});
