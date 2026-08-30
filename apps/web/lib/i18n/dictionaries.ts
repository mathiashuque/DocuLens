import "server-only";

import { notFound } from "next/navigation";

import type { Dictionary } from "./dictionary";
import { isLocale, type Locale } from "./locales";

const loaders: Record<Locale, () => Promise<Dictionary>> = {
  en: () => import("./dictionaries/en").then((module) => module.default),
  es: () => import("./dictionaries/es").then((module) => module.default),
};

/**
 * Loads the dictionary for a route's `lang` param. Only ever called with a
 * value that has already passed through `proxy.ts`, but route params are
 * still untrusted input, so an unsupported value 404s instead of silently
 * rendering English content under the wrong `<html lang>`.
 */
export async function getDictionary(locale: string): Promise<Dictionary> {
  if (!isLocale(locale)) {
    notFound();
  }
  return loaders[locale]();
}
