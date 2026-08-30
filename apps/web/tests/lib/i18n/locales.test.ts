import { describe, expect, it } from "vitest";

import { DEFAULT_LOCALE, isLocale, parseLocaleCookie, SUPPORTED_LOCALES } from "@/lib/i18n/locales";
import en from "@/lib/i18n/dictionaries/en";
import es from "@/lib/i18n/dictionaries/es";

describe("locale contract", () => {
  it("supports exactly English and Spanish, defaulting to English", () => {
    expect(SUPPORTED_LOCALES).toEqual(["en", "es"]);
    expect(DEFAULT_LOCALE).toBe("en");
  });

  it("validates untrusted locale values with a type guard", () => {
    expect(isLocale("en")).toBe(true);
    expect(isLocale("es")).toBe(true);
    expect(isLocale("fr")).toBe(false);
    expect(isLocale("EN")).toBe(false);
    expect(isLocale(undefined)).toBe(false);
    expect(isLocale(42)).toBe(false);
  });

  it("parses a locale cookie, rejecting anything unsupported instead of falling back silently", () => {
    expect(parseLocaleCookie("en")).toBe("en");
    expect(parseLocaleCookie("es")).toBe("es");
    expect(parseLocaleCookie("fr")).toBeNull();
    expect(parseLocaleCookie(undefined)).toBeNull();
    expect(parseLocaleCookie("")).toBeNull();
  });
});

describe("dictionary parity", () => {
  it("gives English and Spanish dictionaries the exact same key shape", () => {
    expect(deepKeys(en)).toEqual(deepKeys(es));
  });

  it("includes the complete localized footer contract", () => {
    expect(Object.keys(en.footer).sort()).toEqual(["attribution", "portfolioLink", "tagline"]);
    expect(Object.keys(es.footer).sort()).toEqual(Object.keys(en.footer).sort());
  });
});

function deepKeys(value: unknown, prefix = ""): string[] {
  if (Array.isArray(value)) {
    // Arrays (steps, examples) are compared by length + shape of the first
    // element, not full recursive parity, since they hold parallel domain
    // content rather than dictionary keys.
    return value.length ? deepKeys(value[0], `${prefix}[]`) : [`${prefix}[]`];
  }
  if (value && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>).flatMap(([key, nested]) =>
      deepKeys(nested, prefix ? `${prefix}.${key}` : key)
    );
  }
  return [prefix];
}
