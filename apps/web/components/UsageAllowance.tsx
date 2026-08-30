"use client";

import { useEffect, useState } from "react";

import type { Dictionary } from "@/lib/i18n/dictionary";
import { interpolate } from "@/lib/i18n/interpolate";
import { FORMATTING_LOCALE, type Locale } from "@/lib/i18n/locales";
import { usageResponseSchema, type UsageResponse } from "@/lib/usage-schema";

function formatResetTime(retryAt: string | null, locale: Locale): string | null {
  if (!retryAt) return null;
  const reset = new Date(retryAt);
  if (Number.isNaN(reset.getTime())) return null;
  return new Intl.DateTimeFormat(FORMATTING_LOCALE[locale], { hour: "numeric", minute: "2-digit" }).format(reset);
}

/**
 * Reserves its own line height even before usage data arrives (and renders
 * nothing, rather than collapsing to zero height, once it's clear there's
 * nothing to show) so its async arrival never shifts the composer or CTA
 * sitting next to it.
 */
export function UsageAllowance({
  dict,
  lang,
  documentId,
}: {
  dict: Dictionary["usage"];
  lang: Locale;
  documentId?: string;
}) {
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    const query = documentId ? `?document_id=${encodeURIComponent(documentId)}` : "";
    fetch(`/api/usage${query}`, { signal: controller.signal })
      .then(async (response) => response.ok ? usageResponseSchema.safeParse(await response.json()) : null)
      .then((result) => {
        if (result?.success) setUsage(result.data);
        setLoaded(true);
      })
      .catch(() => setLoaded(true));
    return () => controller.abort();
  }, [documentId]);

  const visible = usage?.enforced
    ? usage.allowances.filter((item) => documentId ? item.category === "question" : item.category !== "question")
    : [];

  if (loaded && !visible.length) return <div className="h-4" aria-hidden="true" />;

  return (
    <p className="min-h-4 text-xs text-ink-subtle" aria-live="polite">
      {visible.map((item) => {
        const label = dict.categoryLabel[item.category];
        if (item.remaining <= 0) {
          const resetTime = formatResetTime(item.retry_at, lang);
          return resetTime
            ? interpolate(dict.usedUpToday, { label, resetTime })
            : interpolate(dict.usedUpTodayNoReset, { label });
        }
        return interpolate(dict.remaining, { remaining: item.remaining, limit: item.limit, label });
      }).join(" · ")}
    </p>
  );
}
