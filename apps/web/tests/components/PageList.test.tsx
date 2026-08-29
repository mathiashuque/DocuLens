import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PageList } from "@/components/PageList";

describe("PageList", () => {
  it("renders every page in ascending order with its label and text", () => {
    render(
      <PageList
        pages={[
          { page_number: 1, text: "First page text" },
          { page_number: 2, text: "Second page text" },
        ]}
      />
    );

    const headings = screen.getAllByRole("heading", { level: 3 });
    expect(headings.map((heading) => heading.textContent)).toEqual([
      "Page 1",
      "Page 2",
    ]);
    expect(screen.getByText("First page text")).toBeInTheDocument();
    expect(screen.getByText("Second page text")).toBeInTheDocument();
  });

  it("shows an explicit empty-page state for blank pages", () => {
    render(<PageList pages={[{ page_number: 1, text: "" }]} />);

    expect(screen.getByText("No text extracted from this page.")).toBeInTheDocument();
  });

  it("gives each page a stable anchor derived from its page number", () => {
    render(
      <PageList
        pages={[
          { page_number: 1, text: "First" },
          { page_number: 7, text: "Seventh" },
        ]}
      />
    );

    expect(document.getElementById("page-1")).toBeInTheDocument();
    expect(document.getElementById("page-7")).toBeInTheDocument();
  });

  it("renders page text that looks like HTML/script as inert text", () => {
    render(
      <PageList pages={[{ page_number: 1, text: "<img src=x onerror=alert(1)>" }]} />
    );

    expect(document.querySelector("img")).not.toBeInTheDocument();
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeInTheDocument();
  });
});
