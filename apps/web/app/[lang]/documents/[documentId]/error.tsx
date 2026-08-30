"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import en from "@/lib/i18n/dictionaries/en";
import es from "@/lib/i18n/dictionaries/es";
import { isLocale } from "@/lib/i18n/locales";

const DICTS = { en, es };

// Error boundaries are Client Components and cannot use `next/root-params`
// or read server-only dictionaries, so the locale comes from the matched
// route params via `useParams()` and a small client-safe dictionary map.
export default function DocumentError({ reset }: { error: Error; reset: () => void }) {
  const params = useParams<{ lang?: string }>();
  const locale = isLocale(params.lang) ? params.lang : "en";
  const dict = DICTS[locale];

  return (
    <div className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center">
      <h1 className="text-2xl font-semibold text-ink">{dict.document.errorHeading}</h1>
      <p className="text-ink-muted">{dict.document.errorBody}</p>
      <div className="mt-2 flex gap-3">
        <button
          type="button"
          onClick={reset}
          className="inline-flex items-center justify-center rounded-md border border-hairline px-5 py-2.5 text-sm font-semibold text-ink hover:bg-canvas-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent motion-safe:active:scale-[0.98]"
        >
          {dict.document.tryAgain}
        </button>
        <Link
          href={`/${locale}`}
          className="inline-flex items-center justify-center rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white hover:bg-accent-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent motion-safe:active:scale-[0.98]"
        >
          {dict.document.uploadCta}
        </Link>
      </div>
    </div>
  );
}
