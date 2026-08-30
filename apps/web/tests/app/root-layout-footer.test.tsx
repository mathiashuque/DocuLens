import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));
vi.mock("@/components/LanguageSwitcher", () => ({
  LanguageSwitcher: ({ dict }: { dict: { languageSwitcherLabel: string } }) => (
    <nav aria-label={dict.languageSwitcherLabel}>language switcher</nav>
  ),
}));

describe("[lang] shared layout footer", () => {
  it.each([
    ["en", "home content", "View portfolio", "Language"],
    ["es", "document content", "Ver portafolio", "Idioma"],
  ])("renders one localized footer around representative %s route content", async (lang, content, linkLabel, navLabel) => {
    const { default: LangLayout } = await import("@/app/[lang]/layout");
    const tree = await LangLayout({ children: <section>{content}</section>, params: Promise.resolve({ lang }) });
    const document = new DOMParser().parseFromString(renderToStaticMarkup(tree), "text/html");

    expect(document.querySelector("main")?.textContent).toContain(content);
    expect(document.querySelectorAll("footer")).toHaveLength(1);
    expect(document.querySelector(`footer a[href="https://mathiashuque.dev/"]`)?.textContent).toBe(linkLabel);
    expect(document.querySelector(`nav[aria-label="${navLabel}"]`)).not.toBeNull();
    expect(document.querySelector("header a")?.textContent).toContain("DocuLens");
  });
});
