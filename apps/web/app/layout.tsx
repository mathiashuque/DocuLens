import type { Metadata, Viewport } from "next";
import Link from "next/link";

import { getSiteUrl } from "@/lib/site-config";

import "./globals.css";

const description =
  "Upload a PDF, then ask it questions or request analysis. DocuLens grounds every answer in the exact page and quote it came from, and says so when the document doesn't have the answer.";

export const metadata: Metadata = {
  metadataBase: new URL(getSiteUrl()),
  title: {
    template: "%s | DocuLens",
    default: "DocuLens — Ask your documents, with evidence",
  },
  description,
  applicationName: "DocuLens",
  formatDetection: {
    telephone: false,
  },
  openGraph: {
    type: "website",
    siteName: "DocuLens",
    title: "DocuLens — Ask your documents, with evidence",
    description,
    url: "/",
  },
  twitter: {
    card: "summary_large_image",
    title: "DocuLens — Ask your documents, with evidence",
    description,
  },
};

export const viewport: Viewport = {
  themeColor: "#4338ca",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex h-dvh flex-col overflow-hidden bg-canvas font-sans text-ink">
        <header className="shrink-0 border-b border-hairline bg-surface/90 backdrop-blur-sm">
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
        <main className="flex min-h-0 w-full flex-1 flex-col overflow-y-auto">{children}</main>
      </body>
    </html>
  );
}
