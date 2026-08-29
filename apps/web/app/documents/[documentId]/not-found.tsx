import Link from "next/link";

export default function DocumentNotFound() {
  return (
    <div className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center">
      <h1 className="text-2xl font-semibold text-zinc-900">Document not found</h1>
      <p className="text-zinc-600">
        We couldn&rsquo;t find a document with that ID. It may have been removed, or
        the link may be incorrect.
      </p>
      <Link
        href="/"
        className="mt-2 inline-flex items-center justify-center rounded-md bg-zinc-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-zinc-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
      >
        Upload a document
      </Link>
    </div>
  );
}
