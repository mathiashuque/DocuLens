import { describe, expect, it } from "vitest";

import { selectLocaleFromAcceptLanguage } from "@/lib/i18n/accept-language";

describe("selectLocaleFromAcceptLanguage", () => {
  it("matches an exact supported tag", () => {
    expect(selectLocaleFromAcceptLanguage("es")).toBe("es");
    expect(selectLocaleFromAcceptLanguage("en")).toBe("en");
  });

  it("reduces a regional tag to its base language", () => {
    expect(selectLocaleFromAcceptLanguage("es-UY")).toBe("es");
    expect(selectLocaleFromAcceptLanguage("en-GB")).toBe("en");
  });

  it("is case-insensitive", () => {
    expect(selectLocaleFromAcceptLanguage("ES-uy")).toBe("es");
  });

  it("honors quality weights and picks the highest-weighted supported language", () => {
    expect(selectLocaleFromAcceptLanguage("fr;q=0.9, es;q=0.8, en;q=0.5")).toBe("es");
    expect(selectLocaleFromAcceptLanguage("en;q=0.3, es;q=0.9")).toBe("es");
  });

  it("skips unsupported languages to find a supported one further down the list", () => {
    expect(selectLocaleFromAcceptLanguage("fr-FR,de;q=0.9,es;q=0.8")).toBe("es");
  });

  it("falls back to English for the wildcard, unsupported-only, malformed, or missing input", () => {
    expect(selectLocaleFromAcceptLanguage("*")).toBe("en");
    expect(selectLocaleFromAcceptLanguage("fr,de,it")).toBe("en");
    expect(selectLocaleFromAcceptLanguage("not a valid header;;;")).toBe("en");
    expect(selectLocaleFromAcceptLanguage("")).toBe("en");
    expect(selectLocaleFromAcceptLanguage(null)).toBe("en");
    expect(selectLocaleFromAcceptLanguage(undefined)).toBe("en");
  });

  it("ignores a zero-quality entry even when it's listed first", () => {
    expect(selectLocaleFromAcceptLanguage("es;q=0, en;q=0.8")).toBe("en");
  });
});
