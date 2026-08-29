"""Document parsing API response contract."""

from typing import Literal

from pydantic import BaseModel

ParseStatus = Literal["parsed", "ocr_required"]


class DocumentPageResponse(BaseModel):
    page_number: int
    text: str


class ParseDocumentResponse(BaseModel):
    filename: str
    status: ParseStatus
    page_count: int
    pages: list[DocumentPageResponse]
