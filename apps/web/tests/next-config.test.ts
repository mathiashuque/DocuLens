import { afterEach, describe, expect, it, vi } from "vitest";

describe("Next.js output configuration", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("leaves output tracing to Vercel during Vercel builds", async () => {
    vi.stubEnv("VERCEL", "1");

    const { default: config } = await import("../next.config");

    expect(config.output).toBeUndefined();
  });

  it("keeps standalone output for the Docker image", async () => {
    vi.stubEnv("VERCEL", "");

    const { default: config } = await import("../next.config");

    expect(config.output).toBe("standalone");
  });
});
