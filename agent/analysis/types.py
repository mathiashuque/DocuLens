"""Typed structured-output contract produced by the generic analysis
provider, before deterministic validation and ID assignment.
"""

import math

from pydantic import BaseModel, Field, field_validator

from agent.analysis.taxonomy import Importance, Severity

MAX_KEY_TOPICS = 8
MAX_FINDINGS = 10
MAX_DATES = 10
MAX_RISKS = 10


def _finite_unit_interval(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("confidence must be a finite number")
    if not 0.0 <= value <= 1.0:
        raise ValueError("confidence must be within [0, 1]")
    return value


class AnalysisEvidenceItem(BaseModel):
    """One page/quote pair. Evidence must resolve to exact original text."""

    page: int = Field(gt=0)
    text: str

    @field_validator("text")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("evidence text must not be empty")
        return value


class DocumentSummaryCandidate(BaseModel):
    """Generated interpretation, not itself evidence-cited per field."""

    title: str | None = Field(default=None, max_length=200)
    purpose: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=2000)
    key_topics: list[str] = Field(default_factory=list, max_length=MAX_KEY_TOPICS)

    @field_validator("key_topics")
    @classmethod
    def _dedupe_topics(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(topic.strip() for topic in value if topic.strip()))


class FindingCandidate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=1000)
    category: str = Field(min_length=1, max_length=50)
    importance: Importance
    source_page: int = Field(gt=0)
    evidence: str = Field(min_length=1, max_length=1000)
    confidence: float

    @field_validator("confidence")
    @classmethod
    def _confidence(cls, value: float) -> float:
        return _finite_unit_interval(value)


class ImportantDateCandidate(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    raw_value: str = Field(min_length=1, max_length=100)
    normalized_date: str | None = Field(default=None)
    source_page: int = Field(gt=0)
    evidence: str = Field(min_length=1, max_length=1000)
    confidence: float

    @field_validator("confidence")
    @classmethod
    def _confidence(cls, value: float) -> float:
        return _finite_unit_interval(value)


class RiskCandidate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=1000)
    category: str = Field(min_length=1, max_length=50)
    severity: Severity
    evidence: list[AnalysisEvidenceItem] = Field(min_length=1, max_length=3)
    confidence: float

    @field_validator("confidence")
    @classmethod
    def _confidence(cls, value: float) -> float:
        return _finite_unit_interval(value)


class GenericAnalysisCandidate(BaseModel):
    """The full structured result requested from the provider on first pass."""

    summary: DocumentSummaryCandidate
    findings: list[FindingCandidate] = Field(
        default_factory=list, max_length=MAX_FINDINGS
    )
    important_dates: list[ImportantDateCandidate] = Field(
        default_factory=list, max_length=MAX_DATES
    )
    risks: list[RiskCandidate] = Field(default_factory=list, max_length=MAX_RISKS)


class RepairCandidate(BaseModel):
    """Corrected replacements for only the invalid items from a prior pass.

    No `summary`: the summary is not evidence-cited and is never subject to
    the targeted repair retry. Items may be fewer than requested, including
    zero, when the provider correctly omits an unsupported claim instead of
    fabricating a fix.
    """

    findings: list[FindingCandidate] = Field(
        default_factory=list, max_length=MAX_FINDINGS
    )
    important_dates: list[ImportantDateCandidate] = Field(
        default_factory=list, max_length=MAX_DATES
    )
    risks: list[RiskCandidate] = Field(default_factory=list, max_length=MAX_RISKS)
