import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SectionList } from "@/components/SectionList";
import type { DocumentSection } from "@/lib/document-schema";

function section(overrides: Partial<DocumentSection>): DocumentSection {
  return {
    id: "8d68405e-e7e1-4e7f-bb1f-7d42cfc88afd",
    title: "1 Introduction",
    level: 1,
    parent_section_id: null,
    page_start: 1,
    page_end: 1,
    section_path: ["1 Introduction"],
    text: "1 Introduction\nbody",
    ...overrides,
  };
}

describe("SectionList", () => {
  it("explains that no sections exist when the list is empty", () => {
    render(<SectionList sections={[]} />);

    expect(screen.getByText(/No reliable headings were detected/)).toBeInTheDocument();
  });

  it("renders section title, exact page range, and source order", () => {
    const sections = [
      section({ id: "a", title: "1 Introduction", page_start: 1, page_end: 2 }),
      section({
        id: "b",
        title: "1.1 Background",
        level: 2,
        page_start: 2,
        page_end: 2,
        section_path: ["1 Introduction", "1.1 Background"],
      }),
    ];

    render(<SectionList sections={sections} />);

    const headings = screen.getAllByRole("heading", { level: 3 });
    expect(headings.map((heading) => heading.textContent)).toEqual([
      "1 Introduction",
      "1.1 Background",
    ]);
    expect(screen.getByText("Pages 1–2")).toBeInTheDocument();
    expect(screen.getByText("Page 2")).toBeInTheDocument();
    expect(screen.getByText("1 Introduction › 1.1 Background")).toBeInTheDocument();
  });

  it("renders section text as inert text, even when it looks like markup", () => {
    const sections = [
      section({ text: "<script>alert('x')</script> plain content" }),
    ];

    render(<SectionList sections={sections} />);

    expect(document.querySelector("script")).not.toBeInTheDocument();
    expect(screen.getByText(/<script>alert\('x'\)<\/script>/)).toBeInTheDocument();
  });
});
