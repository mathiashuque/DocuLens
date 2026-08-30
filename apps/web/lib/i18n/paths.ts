import { isLocale, type Locale } from "./locales";

/**
 * Splits a pathname into its locale prefix (if any) and the remaining path.
 * Operates on the pathname only — callers preserve query strings and
 * fragments by holding onto the original `URL`/`URLSearchParams` themselves.
 */
export function splitLocaleFromPathname(pathname: string): {
  locale: Locale | null;
  rest: string;
} {
  const segments = pathname.split("/");
  // pathname starts with "/", so segments[0] is "" and segments[1] is the
  // first real segment.
  const candidate = segments[1];
  if (isLocale(candidate)) {
    const rest = "/" + segments.slice(2).join("/");
    return { locale: candidate, rest: rest === "/" ? "/" : rest.replace(/\/+$/, "") || "/" };
  }
  return { locale: null, rest: pathname };
}

/** Prefixes an unprefixed pathname with a locale, without ever double-prefixing. */
export function addLocalePrefix(pathname: string, locale: Locale): string {
  const { rest } = splitLocaleFromPathname(pathname);
  if (rest === "/") return `/${locale}`;
  return `/${locale}${rest}`;
}

/**
 * Replaces the locale segment of an already-prefixed pathname (or adds one
 * if missing), leaving the rest of the path — including dynamic segments
 * like an encoded document ID — untouched.
 */
export function replaceLocalePrefix(pathname: string, locale: Locale): string {
  const { rest } = splitLocaleFromPathname(pathname);
  return rest === "/" ? `/${locale}` : `/${locale}${rest}`;
}

/** Removes a leading locale segment, returning the equivalent unprefixed path. */
export function stripLocalePrefix(pathname: string): string {
  return splitLocaleFromPathname(pathname).rest;
}

/**
 * Builds the equivalent path in another locale for client-side navigation,
 * preserving the current search string and (when available) hash fragment.
 */
export function localizeUrl(url: URL, locale: Locale): string {
  const pathname = replaceLocalePrefix(url.pathname, locale);
  return `${pathname}${url.search}${url.hash}`;
}
