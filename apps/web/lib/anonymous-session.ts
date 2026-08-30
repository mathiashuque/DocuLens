import "server-only";

import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import type { NextRequest, NextResponse } from "next/server";

const COOKIE_NAME = "doculens_anonymous_session";
const VERSION = "v1";
const DEFAULT_MAX_AGE = 60 * 60 * 24 * 30;

function publicMode() {
  return ["1", "true", "yes", "on"].includes((process.env.PUBLIC_DEMO_MODE ?? "").toLowerCase());
}

function settings() {
  const secret = process.env.ANONYMOUS_SESSION_SECRET;
  if (!secret || Buffer.byteLength(secret) < 32) throw new Error("Anonymous session signing is not configured.");
  const maxAge = Number(process.env.ANONYMOUS_SESSION_MAX_AGE_SECONDS ?? DEFAULT_MAX_AGE);
  if (!Number.isInteger(maxAge) || maxAge <= 0) throw new Error("Anonymous session lifetime is invalid.");
  return { secret, maxAge };
}

function signature(payload: string, secret: string) {
  return createHmac("sha256", secret).update(payload).digest("hex");
}

function valid(token: string, secret: string, maxAge: number) {
  const parts = token.split(".");
  if (parts.length !== 4 || parts[0] !== VERSION) return false;
  const payload = parts.slice(0, 3).join(".");
  const expected = Buffer.from(signature(payload, secret));
  const actual = Buffer.from(parts[3]);
  if (expected.length !== actual.length || !timingSafeEqual(expected, actual)) return false;
  const issuedAt = Number(parts[1]);
  return Number.isInteger(issuedAt) && Date.now() / 1000 - issuedAt <= maxAge && issuedAt <= Date.now() / 1000 + 60;
}

export function anonymousSessionFor(request: NextRequest) {
  if (!publicMode()) return { token: null, issued: false, maxAge: 0 };
  const { secret, maxAge } = settings();
  const existing = request.cookies.get(COOKIE_NAME)?.value;
  if (existing && valid(existing, secret, maxAge)) return { token: existing, issued: false, maxAge };
  const payload = `${VERSION}.${Math.floor(Date.now() / 1000)}.${randomBytes(32).toString("base64url")}`;
  return { token: `${payload}.${signature(payload, secret)}`, issued: true, maxAge };
}

export function applyAnonymousCookie(response: NextResponse, session: ReturnType<typeof anonymousSessionFor>) {
  if (session.issued && session.token) {
    response.cookies.set(COOKIE_NAME, session.token, {
      httpOnly: true, sameSite: "lax", secure: publicMode(), path: "/", maxAge: session.maxAge,
    });
  }
  return response;
}

export function anonymousHeader(session: ReturnType<typeof anonymousSessionFor>): HeadersInit | undefined {
  return session.token ? { "x-doculens-anonymous-session": session.token } : undefined;
}
