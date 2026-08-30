"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

import type { Dictionary } from "@/lib/i18n/dictionary";
import { interpolate } from "@/lib/i18n/interpolate";
import { LOCALE_COOKIE_NAME, LOCALE_DISPLAY_NAME, SUPPORTED_LOCALES, type Locale } from "@/lib/i18n/locales";
import { replaceLocalePrefix } from "@/lib/i18n/paths";

const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

/**
 * Persists an explicit language choice client-side. This cookie only ever
 * holds "en" or "es" (validated on read in `proxy.ts`), is not signed, and
 * is a distinct name from the anonymous-session quota cookie so the two
 * never interfere with each other.
 */
function persistLocale(locale: Locale) {
  if (typeof document === "undefined") return;
  document.cookie = `${LOCALE_COOKIE_NAME}=${locale}; path=/; max-age=${COOKIE_MAX_AGE_SECONDS}; SameSite=Lax`;
}

export function LanguageSwitcher({ locale, dict }: { locale: Locale; dict: Dictionary["navigation"] }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const query = searchParams.toString();

  function hrefFor(target: Locale): string {
    const path = replaceLocalePrefix(pathname, target);
    return query ? `${path}?${query}` : path;
  }

  return (
    <nav aria-label={dict.languageSwitcherLabel} className="flex items-center gap-1 text-xs font-medium">
      {SUPPORTED_LOCALES.map((code) => {
        const active = code === locale;
        return (
          <Link
            key={code}
            href={hrefFor(code)}
            hrefLang={code}
            onClick={() => persistLocale(code)}
            aria-current={active ? "true" : undefined}
            aria-label={interpolate(dict.languageOptionAriaLabel, { language: LOCALE_DISPLAY_NAME[code] })}
            className={`rounded-md px-2 py-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
              active ? "bg-accent-soft text-accent-strong" : "text-ink-muted hover:bg-canvas-strong hover:text-ink"
            }`}
          >
            {LOCALE_DISPLAY_NAME[code]}
          </Link>
        );
      })}
    </nav>
  );
}
