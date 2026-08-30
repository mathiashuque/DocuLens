import { lang } from "next/root-params";

import { getDictionary } from "@/lib/i18n/dictionaries";
import { DEFAULT_LOCALE } from "@/lib/i18n/locales";

/**
 * Route-level loading shell for the document chat. Matches `page.tsx`'s
 * outer sizing so there's no layout jump once the real document arrives —
 * this is honest "loading" text, never fake document content or a
 * percentage the API doesn't provide. `loading.tsx` doesn't receive route
 * `params`, so the locale is read via `next/root-params` instead.
 */
export default async function DocumentLoading() {
  const locale = (await lang()) ?? DEFAULT_LOCALE;
  const dict = await getDictionary(locale);
  return (
    <div className="mx-auto flex h-full min-h-0 w-full max-w-[52rem] flex-1 flex-col px-4 sm:px-6">
      <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center" role="status">
        <span
          aria-hidden="true"
          className="h-5 w-5 animate-spin rounded-full border-2 border-hairline border-t-accent"
        />
        <p className="text-sm text-ink-muted">{dict.document.loading}</p>
      </div>
    </div>
  );
}
