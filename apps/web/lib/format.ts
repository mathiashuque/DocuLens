import type { Dictionary } from "./i18n/dictionary";
import { interpolate } from "./i18n/interpolate";
import { FORMATTING_LOCALE, type Locale } from "./i18n/locales";

// Byte units and raw numbers are technically fixed values, not language —
// only the unit *labels* would ever vary by locale, and no supported locale
// currently needs different ones, so this stays locale-independent.
export function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  const units = ["KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = -1;
  do {
    value /= 1024;
    unitIndex += 1;
  } while (value >= 1024 && unitIndex < units.length - 1);

  const decimals = value >= 10 ? 0 : 1;
  return `${value.toFixed(decimals)} ${units[unitIndex]}`;
}

export function formatPageRange(
  pageStart: number,
  pageEnd: number,
  format: Dictionary["format"]
): string {
  return pageStart === pageEnd
    ? interpolate(format.pageSingular, { page: pageStart })
    : interpolate(format.pageRange, { start: pageStart, end: pageEnd });
}

export function formatDateTime(iso: string, locale: Locale): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return new Intl.DateTimeFormat(FORMATTING_LOCALE[locale], {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
