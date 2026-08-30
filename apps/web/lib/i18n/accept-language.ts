import { DEFAULT_LOCALE, isLocale, type Locale } from "./locales";

type WeightedTag = { tag: string; quality: number };

/**
 * Minimal, dependency-free `Accept-Language` parser scoped to exactly the
 * two base languages this app supports. Handles case, regional subtags
 * (`es-UY`, `en-GB`), quality weights, the `*` wildcard, and malformed or
 * missing input — a focused first-party function is enough here, so no
 * negotiation library is pulled in for a two-locale match.
 */
function parseHeader(header: string): WeightedTag[] {
  return header
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const [rawTag, ...params] = part.split(";").map((segment) => segment.trim());
      const tag = rawTag.toLowerCase();
      const qParam = params.find((param) => param.startsWith("q="));
      const quality = qParam ? Number.parseFloat(qParam.slice(2)) : 1;
      return { tag, quality: Number.isFinite(quality) ? quality : 0 };
    })
    .filter((entry) => entry.quality > 0)
    .sort((a, b) => b.quality - a.quality);
}

/** Reduces a BCP-47 tag (`es-uy`, `en`, `*`) to its base language, if supported. */
function baseLanguage(tag: string): Locale | null {
  if (tag === "*") return null;
  const base = tag.split("-")[0];
  return isLocale(base) ? base : null;
}

export function selectLocaleFromAcceptLanguage(header: string | null | undefined): Locale {
  if (!header || !header.trim()) return DEFAULT_LOCALE;

  let entries: WeightedTag[];
  try {
    entries = parseHeader(header);
  } catch {
    return DEFAULT_LOCALE;
  }

  for (const entry of entries) {
    const match = baseLanguage(entry.tag);
    if (match) return match;
  }

  return DEFAULT_LOCALE;
}
