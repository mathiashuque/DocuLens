import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { BackendConfigError, getBackendBaseUrl } from "@/lib/backend-config";

describe("getBackendBaseUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns a normalized origin without a trailing slash", () => {
    vi.stubEnv("DOCULENS_API_BASE_URL", "http://localhost:8000/");

    expect(getBackendBaseUrl()).toBe("http://localhost:8000");
  });

  it("throws a BackendConfigError when unset", () => {
    vi.stubEnv("DOCULENS_API_BASE_URL", "");

    expect(() => getBackendBaseUrl()).toThrow(BackendConfigError);
  });

  it("throws a BackendConfigError for an invalid URL", () => {
    vi.stubEnv("DOCULENS_API_BASE_URL", "not a url");

    expect(() => getBackendBaseUrl()).toThrow(BackendConfigError);
  });

  it("throws a BackendConfigError for a non-http(s) scheme", () => {
    vi.stubEnv("DOCULENS_API_BASE_URL", "ftp://example.com");

    expect(() => getBackendBaseUrl()).toThrow(BackendConfigError);
  });
});
