import Link from "next/link";

import { StatusBadge } from "@/components/StatusBadge";
import type { Document } from "@/lib/document-schema";

/**
 * Compact chat-workspace identity bar: filename and status only. No page
 * counts, upload timestamp, or other document-inspection metadata — the
 * `/documents/[documentId]` route is a focused chat, not a summary dashboard.
 */
export function DocumentHeader({ document }: { document: Document }) {
  return (
    <header className="flex flex-col gap-4 border-b border-hairline pb-6">
      <Link
        href="/"
        className="w-fit text-sm font-medium text-ink-muted hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        &larr; Upload another document
      </Link>

      <div className="flex flex-wrap items-center gap-3">
        <h1 className="min-w-0 break-words text-2xl font-semibold tracking-tight text-ink">
          {document.filename}
        </h1>
        <StatusBadge status={document.status} />
      </div>

      {document.status === "ocr_required" ? (
        <div
          role="alert"
          className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          No usable text could be extracted from this document. It may be a scanned
          image, and OCR is not yet supported, so it cannot be used for Q&A.
        </div>
      ) : null}
    </header>
  );
}
