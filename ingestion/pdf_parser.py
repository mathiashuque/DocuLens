"""Page-preserving PDF text extraction using PyMuPDF."""

from typing import cast

import pymupdf

from ingestion.errors import (
    EncryptedDocumentError,
    MalformedDocumentError,
    PageLimitExceededError,
)
from ingestion.models import DocumentPage, ParsedDocument, ParsedDocumentStatus

PDF_SIGNATURE = b"%PDF-"


def has_pdf_signature(data: bytes) -> bool:
    return data.startswith(PDF_SIGNATURE)


def parse_pdf(data: bytes, *, max_pages: int) -> ParsedDocument:
    """Extract text page by page, preserving physical page numbers.

    Raises MalformedDocumentError, EncryptedDocumentError, or
    PageLimitExceededError for expected, safe-to-report failures.
    """
    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise MalformedDocumentError("The file could not be read as a PDF.") from exc

    try:
        if document.is_encrypted:
            raise EncryptedDocumentError("The PDF is password-protected.")

        page_count = document.page_count
        if page_count > max_pages:
            raise PageLimitExceededError(page_count, max_pages)

        pages = [
            DocumentPage(
                page_number=index + 1, text=document.load_page(index).get_text().strip()
            )
            for index in range(page_count)
        ]
    finally:
        document.close()

    status = "parsed" if any(page.text for page in pages) else "ocr_required"
    return ParsedDocument(
        status=cast(ParsedDocumentStatus, status), page_count=page_count, pages=pages
    )
