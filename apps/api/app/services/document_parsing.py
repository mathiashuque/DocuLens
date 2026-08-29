"""Upload coordination for the document parse endpoint.

Keeps HTTP status-code mapping out of this module: it raises typed errors
that the route maps to responses.
"""

from pathlib import PurePosixPath

from fastapi import UploadFile

from app.core.config import UploadSettings
from ingestion.models import ParsedDocument
from ingestion.pdf_parser import has_pdf_signature, parse_pdf

PDF_CONTENT_TYPE = "application/pdf"
FALLBACK_FILENAME = "document.pdf"
READ_CHUNK_BYTES = 1024 * 1024


class UnsupportedFileTypeError(Exception):
    """Declared content type or file signature is not a supported PDF."""


class UploadTooLargeError(Exception):
    def __init__(self, max_bytes: int) -> None:
        super().__init__(f"Upload exceeds the {max_bytes}-byte limit.")
        self.max_bytes = max_bytes


def sanitize_filename(filename: str | None) -> str:
    if not filename:
        return FALLBACK_FILENAME
    normalized = filename.replace("\\", "/")
    base = PurePosixPath(normalized).name.strip()
    if not base or base in {".", ".."}:
        return FALLBACK_FILENAME
    return base


async def read_bounded_body(upload: UploadFile, max_bytes: int) -> bytes:
    chunks = bytearray()
    while True:
        chunk = await upload.read(READ_CHUNK_BYTES)
        if not chunk:
            break
        chunks.extend(chunk)
        if len(chunks) > max_bytes:
            raise UploadTooLargeError(max_bytes)
    return bytes(chunks)


async def read_and_parse_pdf(
    upload: UploadFile, settings: UploadSettings
) -> tuple[str, ParsedDocument]:
    if upload.content_type != PDF_CONTENT_TYPE:
        raise UnsupportedFileTypeError("Declared content type is not application/pdf.")

    data = await read_bounded_body(upload, settings.max_upload_bytes)

    if not has_pdf_signature(data):
        raise UnsupportedFileTypeError("File signature is not a valid PDF.")

    parsed = parse_pdf(data, max_pages=settings.max_document_pages)
    filename = sanitize_filename(upload.filename)
    return filename, parsed
