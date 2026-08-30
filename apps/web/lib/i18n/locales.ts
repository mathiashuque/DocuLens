/**
 * Single source of truth for the locale contract. Every other i18n module
 * (proxy, dictionaries, path helpers, formatting) imports from here instead
 * of comparing raw locale strings.
 */
export const SUPPORTED_LOCALES = ["en", "es"] as const;

export type Locale = (typeof SUPPORTED_LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "en";

export const LOCALE_COOKIE_NAME = "doculens_lang";

/** Display names for the language selector, written in their own language. */
export const LOCALE_DISPLAY_NAME: Record<Locale, string> = {
  en: "English",
  es: "Español",
};

/**
 * `Intl`/`Date` formatting locale for each supported UI locale. Spanish
 * conventions vary by region (decimal separators, date order); this
 * repository has no target region requirement, so `es-ES` (peninsular
 * Spanish) is the deliberate, documented choice for date/time formatting.
 */
export const FORMATTING_LOCALE: Record<Locale, string> = {
  en: "en-US",
  es: "es-ES",
};

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (SUPPORTED_LOCALES as readonly string[]).includes(value);
}

/** Validates an untrusted cookie value, returning `null` instead of falling back silently. */
export function parseLocaleCookie(value: string | undefined | null): Locale | null {
  return isLocale(value) ? value : null;
}
