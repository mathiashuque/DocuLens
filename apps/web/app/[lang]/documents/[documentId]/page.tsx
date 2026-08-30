import { notFound } from "next/navigation";

import { AskDocuLens } from "@/components/questions/AskDocuLens";
import { CuratedDemoQuestions } from "@/components/questions/CuratedDemoQuestions";
import { DocumentHeader } from "@/components/DocumentHeader";
import { UsageAllowance } from "@/components/UsageAllowance";
import { getDictionary } from "@/lib/i18n/dictionaries";
import type { Locale } from "@/lib/i18n/locales";
import { fetchDocument } from "@/lib/backend-client";
import { BackendError } from "@/lib/errors";

type DocumentPageProps = {
  params: Promise<{ lang: string; documentId: string }>;
};

export default async function DocumentPage({ params }: DocumentPageProps) {
  const { lang: rawLang, documentId } = await params;
  const dict = await getDictionary(rawLang);
  const lang = rawLang as Locale;

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
        <DocumentHeader document={document} dict={dict} />
        {document.demo_slug && !document.demo_questions ? (
          <aside className="mt-4 rounded-card border border-sky-300 bg-sky-50 p-4 text-sm text-sky-950">
            <p className="font-semibold">{dict.document.precomputedDemoTitle}</p>
            <p className="mt-1">{dict.document.precomputedDemoBody}</p>
          </aside>
        ) : null}
      </div>
      {document.demo_questions ? (
        <div className="min-h-0 flex-1 overflow-y-auto pb-6">
          <CuratedDemoQuestions questions={document.demo_questions} dict={dict.questions} />
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col pb-4">
          <AskDocuLens
            documentId={document.id}
            documentStatus={document.status}
            documentPageNumbers={document.pages.map((page) => page.page_number)}
            dict={dict}
            lang={lang}
          />
          <UsageAllowance dict={dict.usage} lang={lang} documentId={document.id} />
        </div>
      )}
    </div>
  );
}
