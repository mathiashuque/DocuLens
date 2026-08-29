import type { Level } from "@/lib/analysis-schema";

const LEVEL_LABELS: Record<Level, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

const LEVEL_STYLES: Record<Level, string> = {
  low: "bg-zinc-50 text-zinc-700 ring-zinc-600/20",
  medium: "bg-amber-50 text-amber-800 ring-amber-600/20",
  high: "bg-orange-50 text-orange-800 ring-orange-600/20",
  critical: "bg-red-50 text-red-800 ring-red-600/20",
};

/**
 * Renders an importance/severity level. The level name is always spelled
 * out in text (never conveyed by color alone) and the `label` prop names
 * what is being rated (e.g. "Importance", "Severity").
 */
export function LevelBadge({ level, label }: { level: Level; label: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${LEVEL_STYLES[level]}`}
    >
      {label}: {LEVEL_LABELS[level]}
    </span>
  );
}
