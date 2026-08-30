import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

describe("home page JSON-LD", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("parses, uses the configured canonical URL, escapes '<', and carries only approved static fields", async () => {
    vi.stubEnv("DOCULENS_SITE_URL", "https://doculens.example.com");
    vi.resetModules();

    const HomePage = (await import("@/app/[lang]/page")).default;
    const element = (await HomePage({ params: Promise.resolve({ lang: "en" }) })) as unknown as {
      props: { children: Array<{ type: string; props: Record<string, unknown> }> };
    };
    const script = element.props.children.find((child) => child?.type === "script");

    expect(script).toBeDefined();
    const html = (script!.props.dangerouslySetInnerHTML as { __html: string }).__html;

    expect(html).not.toContain("<");
    const parsed = JSON.parse(html.replace(/\\u003c/g, "<"));

    expect(parsed).toEqual({
      "@context": "https://schema.org",
      "@type": "WebApplication",
      name: "DocuLens",
      url: "https://doculens.example.com/en",
      description: expect.any(String),
      applicationCategory: "BusinessApplication",
      operatingSystem: "Any (web browser)",
      inLanguage: "en",
    });

    // No pricing, ratings, reviews, org, or user-controlled content.
    expect(parsed).not.toHaveProperty("offers");
    expect(parsed).not.toHaveProperty("aggregateRating");
    expect(parsed).not.toHaveProperty("author");
  });

  it("uses the Spanish canonical URL and language tag for the Spanish route", async () => {
    vi.stubEnv("DOCULENS_SITE_URL", "https://doculens.example.com");
    vi.resetModules();

    const HomePage = (await import("@/app/[lang]/page")).default;
    const element = (await HomePage({ params: Promise.resolve({ lang: "es" }) })) as unknown as {
      props: { children: Array<{ type: string; props: Record<string, unknown> }> };
    };
    const script = element.props.children.find((child) => child?.type === "script");
    const html = (script!.props.dangerouslySetInnerHTML as { __html: string }).__html;
    const parsed = JSON.parse(html.replace(/\\u003c/g, "<"));

    expect(parsed.url).toBe("https://doculens.example.com/es");
    expect(parsed.inLanguage).toBe("es");
  });
});
