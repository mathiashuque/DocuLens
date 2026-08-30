"""Document parsing and persistence API response contracts."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ParseStatus = Literal["parsed", "ocr_required"]


class DemoCitationResponse(BaseModel):
    chunk_id: uuid.UUID
    page: int = Field(gt=0)
    evidence: str = Field(min_length=1)


class DemoQuestionResponse(BaseModel):
    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    status: Literal["answered", "insufficient_evidence"]
    answer: str = Field(min_length=1)
    citations: list[DemoCitationResponse]


class DocumentPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page_number: int
    text: str


class ParseDocumentResponse(BaseModel):
    filename: str
    status: ParseStatus
    page_count: int
    pages: list[DocumentPageResponse]


class DocumentSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    level: int
    parent_section_id: uuid.UUID | None
    page_start: int
    page_end: int
    section_path: list[str]
    text: str


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
    sections: list[DocumentSectionResponse]
    demo_slug: str | None = None
    demo_title: str | None = None
    demo_description: str | None = None
    demo_document_type: str | None = None
    demo_questions: list[DemoQuestionResponse] | None = None


class DemoCardResponse(BaseModel):
    slug: str
    title: str
    description: str
    document_type: Literal["contract", "technical_specification", "generic"]
    page_count: int
    document_id: uuid.UUID
