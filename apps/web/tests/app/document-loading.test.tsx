import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import DocumentLoading from "@/app/documents/[documentId]/loading";

describe("DocumentLoading", () => {
  it("communicates loading honestly without fake document content or a percentage", () => {
    render(<DocumentLoading />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading document…");
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });
});
