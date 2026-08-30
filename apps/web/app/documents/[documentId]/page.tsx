import { notFound } from "next/navigation";

import { AskDocuLens } from "@/components/questions/AskDocuLens";
import { CuratedDemoQuestions } from "@/components/questions/CuratedDemoQuestions";
import { DocumentHeader } from "@/components/DocumentHeader";
import { UsageAllowance } from "@/components/UsageAllowance";
import { fetchDocument } from "@/lib/backend-client";
import { BackendError } from "@/lib/errors";

type DocumentPageProps = {
  params: Promise<{ documentId: string }>;
};

export default async function DocumentPage({ params }: DocumentPageProps) {
  const { documentId } = await params;

  let document;
  try {
    document = await fetchDocument(documentId);
  } catch (error) {
    if (error instanceof BackendError && error.kind === "not_found") {
      notFound();
    }
    throw error;
  }

  return (
    <div className="mx-auto flex h-full min-h-0 w-full max-w-[52rem] flex-1 flex-col px-4 sm:px-6">
      <div className="shrink-0 pt-6">
        <DocumentHeader document={document} />
        {document.demo_slug ? (
          <aside className="mt-4 rounded-card border border-sky-300 bg-sky-50 p-4 text-sm text-sky-950">
            <p className="font-semibold">Precomputed demo</p>
            <p className="mt-1">This synthetic document and its example answers were curated in advance. Loading it does not call an AI provider.</p>
          </aside>
        ) : null}
      </div>
      {document.demo_questions ? (
        <div className="min-h-0 flex-1 overflow-y-auto pb-6">
          <CuratedDemoQuestions questions={document.demo_questions} />
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col pb-4">
          <AskDocuLens
            documentId={document.id}
            documentStatus={document.status}
            documentPageNumbers={document.pages.map((page) => page.page_number)}
          />
          <UsageAllowance documentId={document.id} />
        </div>
      )}
    </div>
  );
}
