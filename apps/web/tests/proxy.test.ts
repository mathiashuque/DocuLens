// @vitest-environment node
import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { proxy } from "@/proxy";

function requestFor(pathname: string, init: { acceptLanguage?: string; cookie?: string } = {}): NextRequest {
  const headers = new Headers();
  if (init.acceptLanguage) headers.set("accept-language", init.acceptLanguage);
  if (init.cookie) headers.set("cookie", init.cookie);
  return new NextRequest(`http://localhost:3000${pathname}`, { headers });
}

describe("proxy locale routing", () => {
  it("passes already-prefixed English and Spanish paths through unmodified", () => {
    expect(proxy(requestFor("/en")).status).toBe(200);
    expect(proxy(requestFor("/es/documents/abc")).status).toBe(200);
  });

  it("redirects an unprefixed path to the default locale when no signal is present", () => {
    const response = proxy(requestFor("/"));
    expect(response.status).toBe(307);
    expect(new URL(response.headers.get("location")!).pathname).toBe("/en");
  });

  it("redirects an unprefixed document path to its locale equivalent, preserving the document ID", () => {
    const response = proxy(requestFor("/documents/5c68e652-ab9d-442d-a5b3-d24b015155ad"));
    const location = new URL(response.headers.get("location")!);
    expect(location.pathname).toBe("/en/documents/5c68e652-ab9d-442d-a5b3-d24b015155ad");
  });

  it("preserves the query string across the redirect", () => {
    const response = proxy(requestFor("/documents/abc?foo=bar&baz=qux"));
    const location = new URL(response.headers.get("location")!);
    expect(location.pathname).toBe("/en/documents/abc");
    expect(location.search).toBe("?foo=bar&baz=qux");
  });

  it("uses a valid locale cookie over Accept-Language", () => {
    const response = proxy(requestFor("/", { cookie: "doculens_lang=es", acceptLanguage: "en" }));
    expect(new URL(response.headers.get("location")!).pathname).toBe("/es");
  });

  it("ignores an invalid locale cookie and falls back to Accept-Language", () => {
    const response = proxy(requestFor("/", { cookie: "doculens_lang=fr", acceptLanguage: "es" }));
    expect(new URL(response.headers.get("location")!).pathname).toBe("/es");
  });

  it("selects a locale from Accept-Language when there is no cookie", () => {
    const response = proxy(requestFor("/", { acceptLanguage: "es-UY,es;q=0.9,en;q=0.5" }));
    expect(new URL(response.headers.get("location")!).pathname).toBe("/es");
  });

  it("404s an unsupported locale-shaped segment instead of rendering English content under it", () => {
    expect(proxy(requestFor("/fr")).status).toBe(404);
    expect(proxy(requestFor("/de/documents/abc")).status).toBe(404);
  });

  it("does not redirect-loop an already-prefixed path even with a conflicting cookie", () => {
    const response = proxy(requestFor("/en/documents/abc", { cookie: "doculens_lang=es" }));
    expect(response.status).toBe(200);
  });
});
