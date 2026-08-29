"use client";

import { useEffect, useState } from "react";

import { usageResponseSchema, type UsageResponse } from "@/lib/usage-schema";

export function UsageAllowance({ documentId }: { documentId?: string }) {
  const [usage, setUsage] = useState<UsageResponse | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const query = documentId ? `?document_id=${encodeURIComponent(documentId)}` : "";
    fetch(`/api/usage${query}`, { signal: controller.signal })
      .then(async (response) => response.ok ? usageResponseSchema.safeParse(await response.json()) : null)
      .then((result) => {
        if (result?.success) setUsage(result.data);
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, [documentId]);

  if (!usage?.enforced) return null;
  const visible = usage.allowances.filter((item) => documentId ? item.category === "question" : item.category !== "question");
  if (!visible.length) return null;

  return (
    <p className="mt-3 text-xs text-zinc-500" aria-live="polite">
      Anonymous allowance: {visible.map((item) => `${item.remaining} of ${item.limit} ${item.category}`).join(" · ")} remaining
    </p>
  );
}
