import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest, NextResponse } from "next/server";

vi.mock("server-only", () => ({}));

import { anonymousSessionFor, applyAnonymousCookie } from "@/lib/anonymous-session";

const SECRET = "frontend-test-secret-that-is-at-least-thirty-two-bytes";

describe("anonymous session cookie", () => {
  afterEach(() => {
    delete process.env.PUBLIC_DEMO_MODE;
    delete process.env.ANONYMOUS_SESSION_SECRET;
  });

  it("issues a signed high-entropy token with production-safe cookie flags", () => {
    process.env.PUBLIC_DEMO_MODE = "true";
    process.env.ANONYMOUS_SESSION_SECRET = SECRET;
    const request = new NextRequest("https://doculens.example/api/usage");
    const session = anonymousSessionFor(request);
    expect(session.token?.split(".")).toHaveLength(4);
    expect(session.token?.length).toBeGreaterThan(100);

    const response = applyAnonymousCookie(NextResponse.json({ ok: true }), session);
    const cookie = response.headers.get("set-cookie");
    expect(cookie).toContain("HttpOnly");
    expect(cookie).toContain("Secure");
    expect(cookie).toContain("SameSite=lax");
    expect(cookie).toContain("Path=/");
  });

  it("reuses valid cookies, rotates tampered ones, and stays absent when disabled", () => {
    process.env.PUBLIC_DEMO_MODE = "true";
    process.env.ANONYMOUS_SESSION_SECRET = SECRET;
    const original = anonymousSessionFor(new NextRequest("https://doculens.example/api/usage"));
    const validRequest = new NextRequest("https://doculens.example/api/usage", {
      headers: { cookie: `doculens_anonymous_session=${original.token}` },
    });
    expect(anonymousSessionFor(validRequest)).toMatchObject({ token: original.token, issued: false });

    const tamperedRequest = new NextRequest("https://doculens.example/api/usage", {
      headers: { cookie: `doculens_anonymous_session=${original.token}x` },
    });
    expect(anonymousSessionFor(tamperedRequest)).toMatchObject({ issued: true });

    process.env.PUBLIC_DEMO_MODE = "false";
    expect(anonymousSessionFor(validRequest)).toEqual({ token: null, issued: false, maxAge: 0 });
  });
});
