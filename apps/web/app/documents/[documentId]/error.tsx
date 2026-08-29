"use client";

import Link from "next/link";

export default function DocumentError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center">
      <h1 className="text-2xl font-semibold text-zinc-900">Something went wrong</h1>
      <p className="text-zinc-600">
        We couldn&rsquo;t load this document right now. Please try again in a moment.
      </p>
      <div className="mt-2 flex gap-3">
        <button
          type="button"
          onClick={reset}
          className="inline-flex items-center justify-center rounded-md border border-zinc-300 px-5 py-2.5 text-sm font-semibold text-zinc-900 hover:bg-zinc-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
        >
          Try again
        </button>
        <Link
          href="/"
          className="inline-flex items-center justify-center rounded-md bg-zinc-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-zinc-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
        >
          Upload a document
        </Link>
      </div>
    </div>
  );
}
