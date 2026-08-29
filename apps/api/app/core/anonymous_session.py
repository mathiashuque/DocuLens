"""Versioned opaque anonymous-session tokens signed with standard-library HMAC."""

import base64
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

TOKEN_VERSION = "v1"


class InvalidAnonymousSessionError(Exception):
    pass


@dataclass(frozen=True)
class AnonymousIdentity:
    session_digest: str


def issue_token(
    secret: str, *, now: int | None = None, random_id: bytes | None = None
) -> str:
    issued_at = int(time.time() if now is None else now)
    opaque = (
        base64.urlsafe_b64encode(random_id or secrets.token_bytes(32))
        .decode()
        .rstrip("=")
    )
    payload = f"{TOKEN_VERSION}.{issued_at}.{opaque}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_token(
    token: str, secret: str, *, max_age_seconds: int, now: int | None = None
) -> AnonymousIdentity:
    parts = token.split(".")
    if len(parts) != 4 or parts[0] != TOKEN_VERSION:
        raise InvalidAnonymousSessionError("Invalid anonymous session.")
    payload = ".".join(parts[:3])
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(parts[3], expected):
        raise InvalidAnonymousSessionError("Invalid anonymous session.")
    try:
        issued_at = int(parts[1])
        opaque = base64.urlsafe_b64decode(parts[2] + "=" * (-len(parts[2]) % 4))
    except (ValueError, TypeError) as exc:
        raise InvalidAnonymousSessionError("Invalid anonymous session.") from exc
    current = int(time.time() if now is None else now)
    if (
        len(opaque) != 32
        or issued_at > current + 60
        or current - issued_at > max_age_seconds
    ):
        raise InvalidAnonymousSessionError("Anonymous session expired or malformed.")
    digest = hmac.new(secret.encode(), opaque, hashlib.sha256).hexdigest()
    return AnonymousIdentity(session_digest=digest)
