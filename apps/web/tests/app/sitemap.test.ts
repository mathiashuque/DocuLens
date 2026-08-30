import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import sitemap from "@/app/sitemap";

describe("sitemap", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("contains only the canonical public localized home URLs with language alternates and no fabricated modification date", () => {
    vi.stubEnv("DOCULENS_SITE_URL", "https://doculens.example.com");

    const result = sitemap();

    expect(result).toHaveLength(2);
    expect(result.map((entry) => entry.url).sort()).toEqual([
      "https://doculens.example.com/en",
      "https://doculens.example.com/es",
    ]);
    expect(result[0].lastModified).toBeUndefined();
    expect(result[0].alternates?.languages).toEqual({
      en: "https://doculens.example.com/en",
      es: "https://doculens.example.com/es",
    });
    expect(result.some((entry) => /\/documents\/|\/api\/|\?/.test(entry.url))).toBe(false);
  });
});
