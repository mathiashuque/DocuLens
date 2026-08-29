import Link from "next/link";

import { StatusBadge } from "@/components/StatusBadge";
import type { Document } from "@/lib/document-schema";
import { formatDateTime } from "@/lib/format";

export function DocumentSummary({ document }: { document: Document }) {
  return (
    <header className="flex flex-col gap-4 border-b border-zinc-200 pb-8">
      <Link
        href="/"
        className="w-fit text-sm font-medium text-zinc-600 hover:text-zinc-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
      >
        &larr; Upload another document
      </Link>

      <div className="flex flex-wrap items-center gap-3">
        <h1 className="min-w-0 break-words text-2xl font-semibold tracking-tight text-zinc-900">
          {document.filename}
        </h1>
        <StatusBadge status={document.status} />
      </div>

      <dl className="flex flex-wrap gap-x-8 gap-y-2 text-sm text-zinc-600">
        <div>
          <dt className="inline font-medium text-zinc-900">Pages: </dt>
          <dd className="inline">{document.page_count}</dd>
        </div>
        <div>
          <dt className="inline font-medium text-zinc-900">Uploaded: </dt>
          <dd className="inline">{formatDateTime(document.created_at)}</dd>
        </div>
      </dl>

      {document.status === "ocr_required" ? (
        <div
          role="alert"
          className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          No usable text could be extracted from this document. It may be a scanned
          image, and OCR is not yet supported — structure and page text below are
          not available.
        </div>
      ) : null}
    </header>
  );
}
