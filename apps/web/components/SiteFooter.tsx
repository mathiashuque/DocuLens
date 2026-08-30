import type { Dictionary } from "@/lib/i18n/dictionary";

export const PORTFOLIO_URL = "https://mathiashuque.dev/";

export function SiteFooter({ dict }: { dict: Dictionary["footer"] }) {
  return (
    <footer className="mt-auto shrink-0 px-6 pb-[max(1rem,env(safe-area-inset-bottom))] pt-4 text-sm text-ink-muted">
      <div className="mx-auto w-full max-w-5xl border-t border-hairline pt-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
          <div className="flex min-w-0 items-center gap-2.5">
            <span
              aria-hidden="true"
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-accent/25 bg-accent-soft text-accent"
            >
              <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.4">
                <path d="M3 2.5h7v8H3z" />
                <path d="M5 5h3M5 7h2" />
                <circle cx="10.5" cy="10.5" r="2.25" />
                <path d="m12.2 12.2 1.3 1.3" />
              </svg>
            </span>
            <p className="leading-5">
              <span className="font-semibold text-ink">DocuLens</span>
              <span aria-hidden="true"> — </span>
              {dict.tagline}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 pl-8 sm:shrink-0 sm:justify-end sm:pl-0">
            <span>{dict.attribution}</span>
            <span aria-hidden="true" className="text-ink-subtle">
              ·
            </span>
            <a
              href={PORTFOLIO_URL}
              className="inline-flex min-h-9 items-center rounded-md px-1 font-semibold text-accent-strong underline decoration-accent/35 underline-offset-4 transition-colors hover:text-accent hover:decoration-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              {dict.portfolioLink}
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
