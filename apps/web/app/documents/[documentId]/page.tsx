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
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-6 py-10">
      <DocumentHeader document={document} />
      {document.demo_slug ? (
        <aside className="rounded-card border border-sky-300 bg-sky-50 p-4 text-sm text-sky-950">
          <p className="font-semibold">Precomputed demo</p>
          <p className="mt-1">This synthetic document and its example answers were curated in advance. Loading it does not call an AI provider.</p>
        </aside>
      ) : null}
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
    </div>
  );
}
