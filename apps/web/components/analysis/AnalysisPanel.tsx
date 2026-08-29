"use client";

import { useState } from "react";

import type { AnalysisLoadResult } from "@/lib/analysis-client";
import { analysisPagesExistIn } from "@/lib/analysis-evidence";
import type { Analysis } from "@/lib/analysis-schema";
import type { DocumentStatus } from "@/lib/document-schema";
import { AnalysisView } from "./AnalysisView";
import { AnalyzeButton } from "./AnalyzeButton";

/**
 * The single client-interaction boundary for the analysis feature: it holds
 * whichever analysis is currently known (loaded via GET, or just returned
 * by a successful POST) and decides which of three states to show. Every
 * render re-checks that the analysis only cites pages that exist on this
 * document — for both the initial GET result and any freshly posted one —
 * since a mismatch means the response cannot be trusted to link safely.
 */
export function AnalysisPanel({
  documentId,
  documentStatus,
  documentPageNumbers,
  initialLoad,
}: {
  documentId: string;
  documentStatus: DocumentStatus;
  documentPageNumbers: number[];
  initialLoad: AnalysisLoadResult;
}) {
  const [analysis, setAnalysis] = useState<Analysis | null>(
    initialLoad.status === "ready" ? initialLoad.analysis : null
  );
  const [loadErrorMessage] = useState<string | null>(
    initialLoad.status === "error" ? initialLoad.message : null
  );

  // An OCR-required document already explains itself in the document
  // summary; it never had extractable text to analyze in the first place.
  if (documentStatus === "ocr_required") {
    return null;
  }

  if (analysis) {
    if (!analysisPagesExistIn(analysis, documentPageNumbers)) {
      return (
        <section
          role="alert"
          className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800"
        >
          This analysis referenced a page that doesn&rsquo;t exist on the loaded
          document, so it can&rsquo;t be shown safely.
        </section>
      );
    }

    return <AnalysisView analysis={analysis} />;
  }

  return (
    <section
      aria-labelledby="analysis-heading"
      className="flex flex-col gap-4 rounded-md border border-zinc-200 bg-white p-5"
    >
      <h2 id="analysis-heading" className="text-lg font-semibold text-zinc-900">
        Analysis
      </h2>
      <p className="text-sm text-zinc-600">
        Generate an AI-assisted, evidence-backed analysis of this document. Every
        claim will cite the exact page and quote it came from.
      </p>

      {loadErrorMessage ? (
        <p role="alert" className="text-sm font-medium text-red-700">
          {loadErrorMessage}
        </p>
      ) : null}

      <AnalyzeButton documentId={documentId} onSuccess={setAnalysis} />
    </section>
  );
}
