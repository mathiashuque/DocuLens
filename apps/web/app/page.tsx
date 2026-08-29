import { UploadForm } from "@/components/UploadForm";

export default function HomePage() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-24">
      <div className="w-full max-w-xl">
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-900 sm:text-4xl">
          Understand complex documents with AI.
        </h1>
        <p className="mt-4 text-base leading-7 text-zinc-600">
          DocuLens is building toward structured, evidence-backed document analysis.
          Today it parses your PDF page by page and detects the section structure
          already in the document — the foundation the rest of the analysis will
          build on.
        </p>

        <div className="mt-10 rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
          <UploadForm />
        </div>
      </div>
    </div>
  );
}
