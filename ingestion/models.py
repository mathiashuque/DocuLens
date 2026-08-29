"""Domain models for page-preserving PDF parsing output."""

from typing import Literal

from pydantic import BaseModel

ParsedDocumentStatus = Literal["parsed", "ocr_required"]


class DocumentPage(BaseModel):
    page_number: int
    text: str


class ParsedDocument(BaseModel):
    status: ParsedDocumentStatus
    page_count: int
    pages: list[DocumentPage]
