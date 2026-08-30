import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const appDir = join(import.meta.dirname, "..", "..", "app");
const publicDir = join(import.meta.dirname, "..", "..", "public");

const PNG_SIGNATURE = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
const MAX_ICON_BYTES = 200_000;

function readPngDimensions(buffer: Buffer) {
  // IHDR chunk starts at byte 8 (after the signature) and the width/height
  // fields sit at offsets 16 and 20 of the file.
  return {
    width: buffer.readUInt32BE(16),
    height: buffer.readUInt32BE(20),
  };
}

describe("favicon.ico", () => {
  it("is a valid multi-size ICO with 16 and 32px PNG-in-ICO frames", () => {
    const buffer = readFileSync(join(appDir, "favicon.ico"));

    expect(buffer.readUInt16LE(0)).toBe(0); // reserved
    expect(buffer.readUInt16LE(2)).toBe(1); // type: icon
    const count = buffer.readUInt16LE(4);
    expect(count).toBeGreaterThanOrEqual(2);

    const sizes: number[] = [];
    for (let i = 0; i < count; i += 1) {
      const entryOffset = 6 + i * 16;
      const width = buffer[entryOffset] === 0 ? 256 : buffer[entryOffset];
      sizes.push(width);
    }
    expect(sizes).toEqual(expect.arrayContaining([16, 32]));
    expect(buffer.length).toBeLessThan(MAX_ICON_BYTES);
  });
});

describe("icon.svg", () => {
  it("is a well-formed square SVG using the accepted accent color", () => {
    const svg = readFileSync(join(appDir, "icon.svg"), "utf-8");

    expect(svg).toMatch(/<svg[^>]*viewBox="0 0 32 32"/);
    expect(svg).toContain("#4338ca");
    expect(svg).not.toMatch(/(?:href|src)\s*=\s*["']https?:\/\//); // no remote references
  });
});

describe("apple-icon.png", () => {
  it("is a 180x180 opaque PNG within a reasonable size budget", () => {
    const buffer = readFileSync(join(appDir, "apple-icon.png"));

    expect(buffer.subarray(0, 8)).toEqual(PNG_SIGNATURE);
    const { width, height } = readPngDimensions(buffer);
    expect(width).toBe(180);
    expect(height).toBe(180);
    expect(buffer.length).toBeLessThan(MAX_ICON_BYTES);
  });
});

describe("manifest icons", () => {
  it.each([
    ["icons/icon-192.png", 192],
    ["icons/icon-512.png", 512],
  ])("%s is a valid square PNG at its declared size", (relativePath, expectedSize) => {
    const buffer = readFileSync(join(publicDir, relativePath));

    expect(buffer.subarray(0, 8)).toEqual(PNG_SIGNATURE);
    const { width, height } = readPngDimensions(buffer);
    expect(width).toBe(expectedSize);
    expect(height).toBe(expectedSize);
  });
});
