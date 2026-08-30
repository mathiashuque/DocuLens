import Link from "next/link";

export default function DocumentNotFound() {
  return (
    <div className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center">
      <h1 className="text-2xl font-semibold text-ink">Document not found</h1>
      <p className="text-ink-muted">
        We couldn&rsquo;t find a document with that ID. It may have been removed, or
        the link may be incorrect.
      </p>
      <Link
        href="/"
        className="mt-2 inline-flex items-center justify-center rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white hover:bg-accent-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent motion-safe:active:scale-[0.98]"
      >
        Upload a document
      </Link>
    </div>
  );
}
