"use client";

import { useEffect, useState } from "react";

import { usageResponseSchema, type UsageResponse } from "@/lib/usage-schema";

const CATEGORY_LABEL: Record<UsageResponse["allowances"][number]["category"], string> = {
  index: "document uploads",
  question: "questions",
  analysis: "analyses",
};

function formatResetTime(retryAt: string | null): string | null {
  if (!retryAt) return null;
  const reset = new Date(retryAt);
  return Number.isNaN(reset.getTime()) ? null : reset.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

/**
 * Reserves its own line height even before usage data arrives (and renders
 * nothing, rather than collapsing to zero height, once it's clear there's
 * nothing to show) so its async arrival never shifts the composer or CTA
 * sitting next to it.
 */
export function UsageAllowance({ documentId }: { documentId?: string }) {
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
        const label = CATEGORY_LABEL[item.category];
        if (item.remaining <= 0) {
          const resetTime = formatResetTime(item.retry_at);
          return `You've used today's free ${label}${resetTime ? ` — more available at ${resetTime}` : ""}.`;
        }
        return `${item.remaining} of ${item.limit} free ${label} left today`;
      }).join(" · ")}
    </p>
  );
}
