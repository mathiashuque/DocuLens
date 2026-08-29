import "server-only";

import { getBackendBaseUrl } from "./backend-config";
import { demoCardsSchema, type DemoCard } from "./demo-schema";

export async function fetchDemos(): Promise<DemoCard[]> {
  try {
    const response = await fetch(`${getBackendBaseUrl()}/api/demos`, {
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    if (!response.ok) return [];
    const parsed = demoCardsSchema.safeParse(await response.json());
    return parsed.success && parsed.data.length === 3 ? parsed.data : [];
  } catch {
    return [];
  }
}
