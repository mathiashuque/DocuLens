import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PORTFOLIO_URL, SiteFooter } from "@/components/SiteFooter";
import en from "@/lib/i18n/dictionaries/en";
import es from "@/lib/i18n/dictionaries/es";

describe("SiteFooter", () => {
  it.each([
    [en.footer, "Evidence over guesswork", "Designed and built by Mathias", "View portfolio"],
    [es.footer, "Evidencia, no suposiciones", "Diseñado y desarrollado por Mathias", "Ver portafolio"],
  ])("renders localized copy and the approved same-tab destination", (dict, tagline, attribution, linkLabel) => {
    render(<SiteFooter dict={dict} />);

    const footer = screen.getByRole("contentinfo");
    expect(within(footer).getByText("DocuLens")).toBeInTheDocument();
    expect(within(footer).getByText(tagline)).toBeInTheDocument();
    expect(within(footer).getByText(attribution)).toBeInTheDocument();

    const link = within(footer).getByRole("link", { name: linkLabel });
    expect(link).toHaveAttribute("href", PORTFOLIO_URL);
    expect(link).not.toHaveAttribute("target");
    expect(within(footer).getAllByRole("link")).toHaveLength(1);
  });

  it("keeps the evidence mark decorative and out of keyboard navigation", () => {
    const { container } = render(<SiteFooter dict={en.footer} />);

    const mark = container.querySelector('[aria-hidden="true"] svg');
    expect(mark).toBeInTheDocument();
    expect(mark?.closest("span")).toHaveAttribute("aria-hidden", "true");
    expect(container.querySelectorAll("svg [tabindex], svg a")).toHaveLength(0);
  });
});
