"""Public grounded-QA request/response contracts.

`status` discriminates `answered` from `insufficient_evidence` so clients can
safely distinguish the two typed outcomes. No retrieval scores, prompts,
model internals, or provider details are ever exposed.
"""

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.services.search import DEFAULT_TOP_K


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=20)


class CitationResponse(BaseModel):
    chunk_id: uuid.UUID
    page: int
    evidence: str


class AnsweredResponse(BaseModel):
    document_id: uuid.UUID
    question: str
    status: Literal["answered"] = "answered"
    answer: str
    citations: list[CitationResponse]


class InsufficientEvidenceResponse(BaseModel):
    document_id: uuid.UUID
    question: str
    status: Literal["insufficient_evidence"] = "insufficient_evidence"
    answer: str
    citations: list[CitationResponse] = Field(default_factory=list)


QuestionResponse = AnsweredResponse | InsufficientEvidenceResponse
