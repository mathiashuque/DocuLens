import { describe, expect, it } from "vitest";
import { existsSync } from "node:fs";
import { join } from "node:path";

import manifest from "@/app/manifest";

describe("manifest", () => {
  it("has aligned name/description/colors/start URL", () => {
    const result = manifest();

    expect(result.name).toBe("DocuLens");
    expect(result.short_name).toBe("DocuLens");
    expect(result.start_url).toBe("/");
    expect(result.theme_color).toBe("#4338ca");
    expect(result.background_color).toBe("#eef1f6");
  });

  it("references icons whose declared size/type match a real committed file", () => {
    const result = manifest();
    const pngIcons = (result.icons ?? []).filter((icon) => icon.type === "image/png");

    expect(pngIcons.length).toBeGreaterThan(0);

    for (const icon of pngIcons) {
      const filePath = join(import.meta.dirname, "..", "..", "public", icon.src.replace(/^\//, ""));
      expect(existsSync(filePath), `${icon.src} should exist`).toBe(true);

      const [width, height] = (icon.sizes ?? "").split("x").map(Number);
      expect(width).toBe(height);
      expect(width).toBeGreaterThan(0);
    }
  });
});
