import type { Metadata } from "next";
import Link from "next/link";

import "./globals.css";

export const metadata: Metadata = {
  title: "DocuLens",
  description:
    "DocuLens turns complex documents into structured, evidence-backed analysis.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-canvas font-sans text-ink">
        <header className="sticky top-0 z-10 border-b border-hairline bg-surface/90 backdrop-blur-sm">
          <div className="mx-auto flex w-full max-w-5xl items-center px-6 py-3">
            <Link
              href="/"
              className="inline-flex items-center gap-2 text-sm font-semibold tracking-tight text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <span
                aria-hidden="true"
                className="flex h-6 w-6 items-center justify-center rounded-md border border-accent/30 bg-accent-soft text-accent"
              >
                <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.4">
                  <rect x="2.5" y="1.5" width="8" height="11" rx="1" />
                  <line x1="4.5" y1="4.5" x2="8.5" y2="4.5" />
                  <line x1="4.5" y1="6.5" x2="8.5" y2="6.5" />
                  <circle cx="10.5" cy="11" r="2.2" />
                  <line x1="12.2" y1="12.7" x2="13.5" y2="14" />
                </svg>
              </span>
              DocuLens
            </Link>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
