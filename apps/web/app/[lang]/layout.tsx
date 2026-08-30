import type { Metadata, Viewport } from "next";
import { Suspense } from "react";
import Link from "next/link";

import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { getDictionary } from "@/lib/i18n/dictionaries";
import { isLocale, SUPPORTED_LOCALES, type Locale } from "@/lib/i18n/locales";
import { getSiteUrl } from "@/lib/site-config";

import "../globals.css";

type LangLayoutProps = {
  children: React.ReactNode;
  params: Promise<{ lang: string }>;
};

export function generateStaticParams() {
  return SUPPORTED_LOCALES.map((lang) => ({ lang }));
}

export async function generateMetadata({ params }: { params: Promise<{ lang: string }> }): Promise<Metadata> {
  const { lang } = await params;
  if (!isLocale(lang)) {
    return {};
  }
  const dict = await getDictionary(lang);
  const siteUrl = getSiteUrl();

  const languageAlternates = Object.fromEntries(SUPPORTED_LOCALES.map((code) => [code, `/${code}`]));

  return {
    metadataBase: new URL(siteUrl),
    title: {
      template: dict.metadata.titleTemplate,
      default: dict.metadata.defaultTitle,
    },
    description: dict.metadata.description,
    applicationName: "DocuLens",
    formatDetection: {
      telephone: false,
    },
    alternates: {
      canonical: `/${lang}`,
      languages: { ...languageAlternates, "x-default": "/en" },
    },
    openGraph: {
      type: "website",
      siteName: "DocuLens",
      title: dict.metadata.defaultTitle,
      description: dict.metadata.description,
      url: `/${lang}`,
      locale: lang === "es" ? "es_ES" : "en_US",
      alternateLocale: lang === "es" ? "en_US" : "es_ES",
    },
    twitter: {
      card: "summary_large_image",
      title: dict.metadata.defaultTitle,
      description: dict.metadata.description,
    },
  };
}

export const viewport: Viewport = {
  themeColor: "#4338ca",
};

export default async function LangLayout({ children, params }: LangLayoutProps) {
  const { lang } = await params;
  // `getDictionary` 404s on an unsupported locale. `proxy.ts` already keeps
  // unsupported locale segments from reaching any page, so this is a
  // defense-in-depth check, not the primary enforcement point.
  const dict = await getDictionary(lang);

  return (
    <html lang={lang} className="h-full antialiased">
      <body className="flex h-dvh flex-col overflow-hidden bg-canvas font-sans text-ink">
        <header className="shrink-0 border-b border-hairline bg-surface/90 backdrop-blur-sm">
          <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-3">
            <Link
              href={`/${lang}`}
              aria-label={dict.navigation.homeLinkAriaLabel}
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
            <Suspense fallback={null}>
              <LanguageSwitcher locale={lang as Locale} dict={dict.navigation} />
            </Suspense>
          </div>
        </header>
        <main className="flex min-h-0 w-full flex-1 flex-col overflow-y-auto">{children}</main>
      </body>
    </html>
  );
}
