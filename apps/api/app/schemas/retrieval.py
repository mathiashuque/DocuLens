"""Public index/search API request and response contracts.

Vectors are never exposed; only chunk text, provenance, and scores.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.services.search import SEARCH_STRATEGY


class IndexResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: uuid.UUID
    status: str
    chunk_count: int
    embedding_provider: str
    embedding_model: str
    dimension: int
    chunker_version: str
    chunking_config: str
    created_at: datetime


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResultResponse(BaseModel):
    chunk_id: uuid.UUID
    chunk_index: int
    text: str
    page_start: int
    page_end: int
    section_id: uuid.UUID | None
    section_title: str | None
    section_path: list[str]
    score: float


class SearchResponse(BaseModel):
    document_id: uuid.UUID
    query: str
    strategy: str = SEARCH_STRATEGY
    results: list[SearchResultResponse]
