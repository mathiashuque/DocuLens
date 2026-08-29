"""Document parsing and persistence API response contracts."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ParseStatus = Literal["parsed", "ocr_required"]


class DocumentPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page_number: int
    text: str


class ParseDocumentResponse(BaseModel):
    filename: str
    status: ParseStatus
    page_count: int
    pages: list[DocumentPageResponse]


class DocumentResponse(BaseModel):
    """Durable representation returned by create and retrieve."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    content_hash: str
    status: ParseStatus
    page_count: int
    created_at: datetime
    pages: list[DocumentPageResponse]
