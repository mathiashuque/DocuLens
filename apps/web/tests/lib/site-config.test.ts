import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { SiteConfigError, getSiteUrl } from "@/lib/site-config";

describe("getSiteUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns a normalized origin without a trailing slash", () => {
    vi.stubEnv("DOCULENS_SITE_URL", "https://doculens.example.com/");

    expect(getSiteUrl()).toBe("https://doculens.example.com");
  });

  it("defaults to localhost outside production when unset", () => {
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("DOCULENS_SITE_URL", "");

    expect(getSiteUrl()).toBe("http://localhost:3000");
  });

  it("throws a SiteConfigError in production when unset", () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("DOCULENS_SITE_URL", "");

    expect(() => getSiteUrl()).toThrow(SiteConfigError);
  });

  it("throws a SiteConfigError for a malformed URL", () => {
    vi.stubEnv("DOCULENS_SITE_URL", "not a url");

    expect(() => getSiteUrl()).toThrow(SiteConfigError);
  });

  it("throws a SiteConfigError for a non-http(s) scheme", () => {
    vi.stubEnv("DOCULENS_SITE_URL", "ftp://doculens.example.com");

    expect(() => getSiteUrl()).toThrow(SiteConfigError);
  });
});
