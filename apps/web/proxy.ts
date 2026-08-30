import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { selectLocaleFromAcceptLanguage } from "@/lib/i18n/accept-language";
import { DEFAULT_LOCALE, LOCALE_COOKIE_NAME, parseLocaleCookie } from "@/lib/i18n/locales";
import { addLocalePrefix, splitLocaleFromPathname } from "@/lib/i18n/paths";

// Any two-lowercase-letter first segment that isn't one of our supported
// locales (e.g. "/fr") is treated as an unsupported locale request, not as
// an unprefixed page path — it must 404 rather than silently render English
// content under an incorrect `<html lang>`.
const LOCALE_LIKE_SEGMENT = /^[a-z]{2}$/;

export function proxy(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  const { locale: prefixLocale } = splitLocaleFromPathname(pathname);

  // Already locale-prefixed (/en/*, /es/*) — leave it alone.
  if (prefixLocale) {
    return NextResponse.next();
  }

  const firstSegment = pathname.split("/")[1] ?? "";
  if (LOCALE_LIKE_SEGMENT.test(firstSegment)) {
    return new NextResponse(null, { status: 404 });
  }

  const cookieLocale = parseLocaleCookie(request.cookies.get(LOCALE_COOKIE_NAME)?.value);
  const locale =
    cookieLocale ?? selectLocaleFromAcceptLanguage(request.headers.get("accept-language")) ?? DEFAULT_LOCALE;

  // Fragments never reach the server, so they can't be forwarded here; the
  // browser reattaches the original fragment to the redirected URL itself.
  const destination = request.nextUrl.clone();
  destination.pathname = addLocalePrefix(pathname, locale);
  return NextResponse.redirect(destination);
}

export const config = {
  matcher: [
    "/((?!api/|_next/static|_next/image|_next/data|favicon.ico|icon.svg|apple-icon.png|opengraph-image|twitter-image|manifest.webmanifest|robots.txt|sitemap.xml|icons/).*)",
  ],
};
