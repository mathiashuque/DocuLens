"""Final, app-ID-assigned generic analysis result.

IDs are generated here, in application code — never trusted from the
provider. This is what the graph produces and the API service persists.
"""

import uuid
from dataclasses import dataclass, field

from agent.analysis.provider import ProviderMetadata
from agent.analysis.types import (
    DocumentSummaryCandidate,
    FindingCandidate,
    ImportantDateCandidate,
    RiskCandidate,
)
from agent.extractors.contract.result import ContractAnalysisResult


@dataclass(frozen=True)
class FindingResult:
    id: uuid.UUID
    title: str
    description: str
    category: str
    importance: str
    source_page: int
    evidence: str
    confidence: float


@dataclass(frozen=True)
class ImportantDateResult:
    id: uuid.UUID
    label: str
    raw_value: str
    normalized_date: str | None
    source_page: int
    evidence: str
    confidence: float


@dataclass(frozen=True)
class RiskEvidenceResult:
    page: int
    text: str


@dataclass(frozen=True)
class RiskResult:
    id: uuid.UUID
    title: str
    description: str
    category: str
    severity: str
    evidence: tuple[RiskEvidenceResult, ...]
    confidence: float


@dataclass(frozen=True)
class GenericAnalysisResult:
    summary: DocumentSummaryCandidate
    findings: tuple[FindingResult, ...] = field(default_factory=tuple)
    important_dates: tuple[ImportantDateResult, ...] = field(default_factory=tuple)
    risks: tuple[RiskResult, ...] = field(default_factory=tuple)
    provider: str = ""
    model: str = ""
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    retry_count: int = 0
    specialized: ContractAnalysisResult | None = None


class AnalysisFailedError(Exception):
    """The candidate (or its one repair attempt) still had invalid items, or
    the run failed for another safe, typed reason.

    No completed analysis is persisted; the caller maps this to a safe
    HTTP 502.
    """


def assign_ids(
    *,
    summary: DocumentSummaryCandidate,
    findings: list[FindingCandidate],
    dates: list[ImportantDateCandidate],
    risks: list[RiskCandidate],
    metadata: ProviderMetadata,
    retry_count: int,
    specialized: ContractAnalysisResult | None = None,
) -> GenericAnalysisResult:
    return GenericAnalysisResult(
        summary=summary,
        findings=tuple(
            FindingResult(
                id=uuid.uuid4(),
                title=item.title,
                description=item.description,
                category=item.category,
                importance=item.importance,
                source_page=item.source_page,
                evidence=item.evidence,
                confidence=item.confidence,
            )
            for item in findings
        ),
        important_dates=tuple(
            ImportantDateResult(
                id=uuid.uuid4(),
                label=item.label,
                raw_value=item.raw_value,
                normalized_date=item.normalized_date,
                source_page=item.source_page,
                evidence=item.evidence,
                confidence=item.confidence,
            )
            for item in dates
        ),
        risks=tuple(
            RiskResult(
                id=uuid.uuid4(),
                title=item.title,
                description=item.description,
                category=item.category,
                severity=item.severity,
                evidence=tuple(
                    RiskEvidenceResult(page=e.page, text=e.text) for e in item.evidence
                ),
                confidence=item.confidence,
            )
            for item in risks
        ),
        provider=metadata.provider,
        model=metadata.model,
        latency_ms=metadata.latency_ms,
        input_tokens=metadata.input_tokens,
        output_tokens=metadata.output_tokens,
        retry_count=retry_count,
        specialized=specialized,
    )
