import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import sitemap from "@/app/sitemap";

describe("sitemap", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("contains only the canonical public home URL with no fabricated modification date", () => {
    vi.stubEnv("DOCULENS_SITE_URL", "https://doculens.example.com");

    const result = sitemap();

    expect(result).toHaveLength(1);
    expect(result[0].url).toBe("https://doculens.example.com");
    expect(result[0].lastModified).toBeUndefined();
    expect(result.some((entry) => /\/documents\/|\/api\/|\?/.test(entry.url))).toBe(false);
  });
});
