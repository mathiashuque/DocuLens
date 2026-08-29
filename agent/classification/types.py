"""Typed structured-output contract produced by a classification provider."""

import math

from pydantic import BaseModel, Field, field_validator, model_validator

from agent.classification.taxonomy import DocumentType


class ClassificationEvidenceItem(BaseModel):
    """One page/quote pair supporting a classification candidate."""

    page: int = Field(gt=0)
    text: str

    @field_validator("text")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("evidence text must not be empty")
        return value


class ClassificationCandidate(BaseModel):
    """Raw structured output requested from a provider, before validation."""

    document_type: DocumentType
    confidence: float
    reason: str = Field(min_length=1, max_length=1000)
    evidence: list[ClassificationEvidenceItem] = Field(min_length=1, max_length=3)

    @field_validator("confidence")
    @classmethod
    def _finite_unit_interval(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("confidence must be a finite number")
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be within [0, 1]")
        return value

    @model_validator(mode="after")
    def _reason_non_blank(self) -> "ClassificationCandidate":
        if not self.reason.strip():
            raise ValueError("reason must not be blank")
        return self
