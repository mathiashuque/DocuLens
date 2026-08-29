import { notFound } from "next/navigation";

import { DocumentSummary } from "@/components/DocumentSummary";
import { PageList } from "@/components/PageList";
import { SectionList } from "@/components/SectionList";
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
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-10 px-6 py-16">
      <DocumentSummary document={document} />
      <SectionList sections={document.sections} />
      <PageList pages={document.pages} />
    </div>
  );
}
