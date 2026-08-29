import type { DocumentStatus } from "@/lib/document-schema";

const LABELS: Record<DocumentStatus, string> = {
  parsed: "Parsed",
  ocr_required: "OCR required",
};

const STYLES: Record<DocumentStatus, string> = {
  parsed: "bg-emerald-50 text-emerald-800 ring-emerald-600/20",
  ocr_required: "bg-amber-50 text-amber-800 ring-amber-600/20",
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${STYLES[status]}`}
    >
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-current" />
      {LABELS[status]}
    </span>
  );
}
