import { notFound } from "next/navigation";

import { AnalysisPanel } from "@/components/analysis/AnalysisPanel";
import { AskDocuLens } from "@/components/questions/AskDocuLens";
import { CuratedDemoQuestions } from "@/components/questions/CuratedDemoQuestions";
import { DocumentSummary } from "@/components/DocumentSummary";
import { PageList } from "@/components/PageList";
import { SectionList } from "@/components/SectionList";
import { UsageAllowance } from "@/components/UsageAllowance";
import { loadAnalysis } from "@/lib/analysis-client";
import { fetchDocument } from "@/lib/backend-client";
import { BackendError } from "@/lib/errors";

type DocumentPageProps = {
  params: Promise<{ documentId: string }>;
};

export default async function DocumentPage({ params }: DocumentPageProps) {
  const { documentId } = await params;

  // Fetch the document and its analysis in parallel — "no completed
  // analysis yet" and backend/analysis failures are page-level states of
  // their own (handled by AnalysisPanel), never a reason to wait on or fail
  // the document fetch, and never a reason to serialize the two requests.
  const [documentOutcome, analysisLoad] = await Promise.all([
    fetchDocument(documentId).then(
      (document) => ({ ok: true as const, document }),
      (error: unknown) => ({ ok: false as const, error })
    ),
    loadAnalysis(documentId),
  ]);

  if (!documentOutcome.ok) {
    const error = documentOutcome.error;
    if (error instanceof BackendError && error.kind === "not_found") {
      notFound();
    }
    throw error;
  }

  const document = documentOutcome.document;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-10 px-6 py-16">
      <DocumentSummary document={document} />
      {document.demo_slug ? (
        <aside className="rounded-card border border-sky-300 bg-sky-50 p-4 text-sm text-sky-950">
          <p className="font-semibold">Precomputed demo</p>
          <p className="mt-1">This synthetic document, analysis, and its example answers were curated in advance. Loading it does not call an AI provider.</p>
        </aside>
      ) : null}
      <AnalysisPanel
        documentId={document.id}
        documentStatus={document.status}
        documentPageNumbers={document.pages.map((page) => page.page_number)}
        initialLoad={analysisLoad}
      />
      {document.demo_questions ? (
        <CuratedDemoQuestions questions={document.demo_questions} />
      ) : (
        <div>
          <AskDocuLens
            documentId={document.id}
            documentStatus={document.status}
            documentPageNumbers={document.pages.map((page) => page.page_number)}
          />
          <UsageAllowance documentId={document.id} />
        </div>
      )}
      <SectionList sections={document.sections} />
      <PageList pages={document.pages} />
    </div>
  );
}
