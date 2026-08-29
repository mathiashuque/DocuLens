import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DemoCards } from "@/components/DemoCards";

const demos = ["contract", "technical_specification", "generic"].map((type, index) => ({
  slug: `demo-${index}`,
  title: `Demo ${index}`,
  description: "Synthetic example.",
  document_type: type as "contract" | "technical_specification" | "generic",
  page_count: 3,
  document_id: `${index + 1}c68e652-ab9d-442d-a5b3-d24b015155ad`.slice(0, 36),
}));

describe("DemoCards", () => {
  it("renders exactly three safe example links", () => {
    render(<DemoCards demos={demos} />);
    expect(screen.getAllByRole("link", { name: "Open demo" })).toHaveLength(3);
  });

  it("keeps upload available through a quiet unseeded state", () => {
    render(<DemoCards demos={[]} />);
    expect(screen.getByText(/Examples are not available/)).toBeInTheDocument();
  });
});
