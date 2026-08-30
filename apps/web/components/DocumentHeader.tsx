import { StatusBadge } from "@/components/StatusBadge";
import type { Dictionary } from "@/lib/i18n/dictionary";
import type { Document } from "@/lib/document-schema";

/**
 * Compact chat-workspace identity strip: filename and status only. No back
 * link of its own — the global brand mark in the app shell already goes
 * home, so this doesn't duplicate that affordance in a second header-shaped
 * row. No page counts, upload timestamp, or other inspection metadata — the
 * `/documents/[documentId]` route is a focused chat, not a summary dashboard.
 */
export function DocumentHeader({ document, dict }: { document: Document; dict: Dictionary }) {
  return (
    <div className="flex flex-col gap-3 border-b border-hairline pb-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <h1 className="min-w-0 break-words text-lg font-semibold tracking-tight text-ink">
          {document.filename}
        </h1>
        <StatusBadge status={document.status} dict={dict.status} />
      </div>

      {document.status === "ocr_required" ? (
        <div
          role="alert"
          className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          {dict.document.ocrRequiredBody}
        </div>
      ) : null}
    </div>
  );
}
