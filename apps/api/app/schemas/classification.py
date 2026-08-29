"""Public classification API response contract."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from agent.classification.taxonomy import DocumentType


class ClassificationEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page: int
    text: str


class ClassificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    document_type: DocumentType
    confidence: float
    reason: str
    evidence: list[ClassificationEvidenceResponse]
    provider: str
    model: str
    status: Literal["completed"]
    created_at: datetime
