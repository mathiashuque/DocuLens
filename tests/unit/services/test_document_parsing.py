"""Deterministic tests for upload filename sanitization and bounded reads."""

import io

import pytest
from app.services.document_parsing import (
    UploadTooLargeError,
    read_bounded_body,
    sanitize_filename,
)
from starlette.datastructures import UploadFile


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "document.pdf"),
        ("", "document.pdf"),
        ("report.pdf", "report.pdf"),
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("..\\..\\windows\\report.pdf", "report.pdf"),
        (".", "document.pdf"),
        ("..", "document.pdf"),
    ],
)
def test_sanitize_filename(raw: str | None, expected: str) -> None:
    assert sanitize_filename(raw) == expected


@pytest.mark.asyncio
async def test_read_bounded_body_allows_exact_limit() -> None:
    upload = UploadFile(filename="f.pdf", file=io.BytesIO(b"a" * 10))

    data = await read_bounded_body(upload, max_bytes=10)

    assert data == b"a" * 10


@pytest.mark.asyncio
async def test_read_bounded_body_rejects_over_limit() -> None:
    upload = UploadFile(filename="f.pdf", file=io.BytesIO(b"a" * 11))

    with pytest.raises(UploadTooLargeError):
        await read_bounded_body(upload, max_bytes=10)
