import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

describe("[lang] layout metadata", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("sets a title template, accurate description, metadataBase, Open Graph, Twitter, and language alternates for English", async () => {
    vi.stubEnv("DOCULENS_SITE_URL", "https://doculens.example.com");
    vi.resetModules();

    const { generateMetadata } = await import("@/app/[lang]/layout");
    const metadata = await generateMetadata({ params: Promise.resolve({ lang: "en" }) });

    expect(metadata.title).toEqual({
      template: "%s | DocuLens",
      default: "DocuLens — Ask your documents, with evidence",
    });
    expect(metadata.metadataBase?.toString()).toBe("https://doculens.example.com/");
    expect(metadata.description).toMatch(/upload a pdf/i);
    expect(metadata.description).not.toMatch(/legal|ocr|unlimited|certified/i);

    expect(metadata.alternates).toMatchObject({
      canonical: "/en",
      languages: { en: "/en", es: "/es", "x-default": "/en" },
    });
    expect(metadata.openGraph?.url).toBe("/en");
    expect(metadata.openGraph?.locale).toBe("en_US");
    expect(metadata.twitter).toMatchObject({ card: "summary_large_image" });
  });

  it("localizes title, description, and canonical for Spanish", async () => {
    vi.stubEnv("DOCULENS_SITE_URL", "https://doculens.example.com");
    vi.resetModules();

    const { generateMetadata } = await import("@/app/[lang]/layout");
    const metadata = await generateMetadata({ params: Promise.resolve({ lang: "es" }) });

    expect(metadata.title).toMatchObject({ default: expect.stringMatching(/DocuLens/) });
    expect(metadata.description).toMatch(/sube un pdf/i);
    expect(metadata.alternates).toMatchObject({ canonical: "/es" });
    expect(metadata.openGraph?.locale).toBe("es_ES");
  });

  it("returns empty metadata for an unsupported locale rather than defaulting to English", async () => {
    vi.resetModules();
    const { generateMetadata } = await import("@/app/[lang]/layout");
    const metadata = await generateMetadata({ params: Promise.resolve({ lang: "fr" }) });
    expect(metadata).toEqual({});
  });
});
