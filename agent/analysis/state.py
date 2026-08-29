"""Strongly typed shared state for the generic analysis graph.

Carries only what nodes need: document identity, ordered pages/context,
classification, typed candidate/result pieces, field-specific validation
issues, retry count, and status. No opaque framework messages, chain of
thought, raw provider payloads, or secrets — and no database session or HTTP
object; those stay at the service boundary that invokes this graph.
"""

from typing import Literal, TypedDict

from agent.analysis.provider import ProviderMetadata, StructuredAnalysisProvider
from agent.analysis.result import GenericAnalysisResult
from agent.analysis.types import (
    DocumentSummaryCandidate,
    FindingCandidate,
    ImportantDateCandidate,
    RiskCandidate,
)
from agent.classification.context import ClassificationContext
from agent.classification.taxonomy import DocumentType

AnalysisStatus = Literal["pending", "completed", "failed"]


class InvalidItem(TypedDict):
    kind: Literal["finding", "date", "risk"]
    description: str
    error: str


class AnalysisState(TypedDict, total=False):
    # Identity and inputs, set once before the graph runs.
    document_id: str
    filename: str
    pages: list[tuple[int, str]]
    section_titles: list[str]
    provider: StructuredAnalysisProvider
    budget_chars: int

    # Set by ensure_classification (resolved by the service before invoking
    # the graph; this node only asserts presence — see its docstring).
    document_type: DocumentType
    classification_confidence: float

    # Set by build_extraction_context.
    context: ClassificationContext

    # Working candidate pieces.
    summary: DocumentSummaryCandidate | None
    pending_findings: list[FindingCandidate]
    pending_dates: list[ImportantDateCandidate]
    pending_risks: list[RiskCandidate]

    # Accumulated validated items (preserved across the retry pass).
    valid_findings: list[FindingCandidate]
    valid_dates: list[ImportantDateCandidate]
    valid_risks: list[RiskCandidate]

    invalid_items: list[InvalidItem]
    retry_count: int

    provider_metadata: ProviderMetadata | None

    status: AnalysisStatus
    failure_reason: str | None
    result: GenericAnalysisResult | None
