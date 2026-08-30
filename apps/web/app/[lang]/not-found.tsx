import { lang } from "next/root-params";
import Link from "next/link";

import { getDictionary } from "@/lib/i18n/dictionaries";
import { DEFAULT_LOCALE } from "@/lib/i18n/locales";

// Catches any unmatched path within a locale segment (e.g. a mistyped or
// removed route). Distinct from the document-specific not-found, which uses
// document-domain copy ("Document not found") instead of this generic one.
export default async function LocaleNotFound() {
  const locale = (await lang()) ?? DEFAULT_LOCALE;
  const dict = await getDictionary(locale);
  return (
    <div className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center justify-center gap-4 px-6 py-24 text-center">
      <h1 className="text-2xl font-semibold text-ink">{dict.notFound.heading}</h1>
      <p className="text-ink-muted">{dict.notFound.body}</p>
      <Link
        href={`/${locale}`}
        className="mt-2 inline-flex items-center justify-center rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white hover:bg-accent-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent motion-safe:active:scale-[0.98]"
      >
        {dict.notFound.homeCta}
      </Link>
    </div>
  );
}
