import pytest
from app.core.anonymous_session import (
    InvalidAnonymousSessionError,
    issue_token,
    verify_token,
)

SECRET = "test-only-secret-that-is-at-least-thirty-two-bytes"


def test_token_is_versioned_opaque_and_verifies_to_digest_only() -> None:
    token = issue_token(SECRET, now=1000, random_id=b"a" * 32)
    identity = verify_token(token, SECRET, max_age_seconds=3600, now=1001)

    assert token.startswith("v1.1000.")
    assert len(identity.session_digest) == 64
    assert "a" * 32 not in identity.session_digest


def test_default_tokens_use_fresh_high_entropy_identifiers() -> None:
    first = issue_token(SECRET, now=1000)
    second = issue_token(SECRET, now=1000)
    assert first != second
    assert len(first.split(".")[2]) >= 43


@pytest.mark.parametrize(
    "token",
    ["", "v2.1.bad.sig", "v1.bad.bad.bad", "v1.1.bad.bad"],
)
def test_malformed_or_unknown_tokens_are_rejected(token: str) -> None:
    with pytest.raises(InvalidAnonymousSessionError):
        verify_token(token, SECRET, max_age_seconds=10, now=20)


def test_tampered_and_expired_tokens_are_rejected() -> None:
    token = issue_token(SECRET, now=1000, random_id=b"b" * 32)
    with pytest.raises(InvalidAnonymousSessionError):
        verify_token(token + "0", SECRET, max_age_seconds=3600, now=1001)
    with pytest.raises(InvalidAnonymousSessionError):
        verify_token(token, SECRET, max_age_seconds=10, now=1011)
