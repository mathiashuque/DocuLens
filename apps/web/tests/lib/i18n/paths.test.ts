import { describe, expect, it } from "vitest";

import {
  addLocalePrefix,
  localizeUrl,
  replaceLocalePrefix,
  splitLocaleFromPathname,
  stripLocalePrefix,
} from "@/lib/i18n/paths";

describe("splitLocaleFromPathname", () => {
  it("extracts a supported locale prefix and the remaining path", () => {
    expect(splitLocaleFromPathname("/en/documents/abc")).toEqual({ locale: "en", rest: "/documents/abc" });
    expect(splitLocaleFromPathname("/es")).toEqual({ locale: "es", rest: "/" });
  });

  it("returns a null locale for an unprefixed or unsupported path", () => {
    expect(splitLocaleFromPathname("/documents/abc")).toEqual({ locale: null, rest: "/documents/abc" });
    expect(splitLocaleFromPathname("/fr/documents/abc")).toEqual({ locale: null, rest: "/fr/documents/abc" });
    expect(splitLocaleFromPathname("/")).toEqual({ locale: null, rest: "/" });
  });
});

describe("addLocalePrefix", () => {
  it("prefixes an unprefixed path without double-prefixing an already-prefixed one", () => {
    expect(addLocalePrefix("/documents/abc", "en")).toBe("/en/documents/abc");
    expect(addLocalePrefix("/", "es")).toBe("/es");
    expect(addLocalePrefix("/en/documents/abc", "es")).toBe("/es/documents/abc");
  });

  it("preserves an encoded dynamic document ID segment", () => {
    const encoded = encodeURIComponent("weird id/slash");
    expect(addLocalePrefix(`/documents/${encoded}`, "en")).toBe(`/en/documents/${encoded}`);
  });
});

describe("replaceLocalePrefix", () => {
  it("swaps the locale segment of an already-prefixed path", () => {
    expect(replaceLocalePrefix("/en/documents/abc", "es")).toBe("/es/documents/abc");
    expect(replaceLocalePrefix("/en", "es")).toBe("/es");
  });
});

describe("stripLocalePrefix", () => {
  it("removes a leading locale segment", () => {
    expect(stripLocalePrefix("/en/documents/abc")).toBe("/documents/abc");
    expect(stripLocalePrefix("/documents/abc")).toBe("/documents/abc");
  });
});

describe("localizeUrl", () => {
  it("preserves the query string and hash while switching locale", () => {
    const url = new URL("https://doculens.example.com/en/documents/abc?x=1#section");
    expect(localizeUrl(url, "es")).toBe("/es/documents/abc?x=1#section");
  });

  it("preserves query strings with multiple params and no hash", () => {
    const url = new URL("https://doculens.example.com/en?x=1&y=2");
    expect(localizeUrl(url, "es")).toBe("/es?x=1&y=2");
  });
});
