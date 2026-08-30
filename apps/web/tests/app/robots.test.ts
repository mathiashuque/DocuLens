import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import robots from "@/app/robots";

describe("robots", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("allows the public root, disallows document/API paths, and links the absolute sitemap", () => {
    vi.stubEnv("DOCULENS_SITE_URL", "https://doculens.example.com");

    const result = robots();

    expect(result.rules).toEqual({
      userAgent: "*",
      allow: "/",
      disallow: ["/documents/", "/api/"],
    });
    expect(result.sitemap).toBe("https://doculens.example.com/sitemap.xml");
  });
});
