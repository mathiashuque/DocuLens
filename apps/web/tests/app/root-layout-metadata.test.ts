import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

describe("root layout metadata", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("sets a title template, accurate description, metadataBase, Open Graph, and Twitter card", async () => {
    vi.stubEnv("DOCULENS_SITE_URL", "https://doculens.example.com");
    vi.resetModules();

    const { metadata } = await import("@/app/layout");

    expect(metadata.title).toEqual({
      template: "%s | DocuLens",
      default: "DocuLens — Ask your documents, with evidence",
    });
    expect(metadata.metadataBase?.toString()).toBe("https://doculens.example.com/");
    expect(metadata.description).toMatch(/upload a pdf/i);
    expect(metadata.description).not.toMatch(/legal|ocr|unlimited|certified/i);

    expect(metadata.openGraph?.url).toBe("/");
    expect(metadata.twitter).toMatchObject({ card: "summary_large_image" });
  });
});
