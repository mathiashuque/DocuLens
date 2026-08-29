import type { Priority } from "@/lib/analysis-schema";

const PRIORITY_LABELS: Record<Priority, string> = {
  must: "Must",
  should: "Should",
  may: "May",
  unspecified: "Unspecified",
};

export function PriorityBadge({ priority }: { priority: Priority }) {
  return (
    <span className="inline-flex items-center rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-700 ring-1 ring-inset ring-zinc-500/20">
      Priority: {PRIORITY_LABELS[priority]}
    </span>
  );
}
