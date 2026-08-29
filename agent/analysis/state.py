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
from agent.extractors.contract.context import SectionSpan
from agent.extractors.contract.provider import (
    ProviderMetadata as ContractProviderMetadata,
)
from agent.extractors.contract.provider import StructuredContractProvider
from agent.extractors.contract.result import ContractAnalysisResult
from agent.extractors.contract.types import (
    ClauseCandidate,
    ObligationCandidate,
    PartyCandidate,
    PaymentTermCandidate,
)

AnalysisStatus = Literal["pending", "completed", "failed"]


class InvalidItem(TypedDict):
    kind: Literal[
        "finding",
        "date",
        "risk",
        "party",
        "obligation",
        "payment_term",
        "clause",
    ]
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
    sections: list[SectionSpan]

    # Only set when document_type == "contract"; the contract route's
    # provider. Absent for generic/technical_specification so no contract
    # provider call is even possible outside that route.
    contract_provider: StructuredContractProvider

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

    # Contract route working/accumulated candidate pieces. Empty for
    # generic/technical_specification documents.
    contract_context: ClassificationContext
    pending_parties: list[PartyCandidate]
    pending_obligations: list[ObligationCandidate]
    pending_payment_terms: list[PaymentTermCandidate]
    pending_clauses: list[ClauseCandidate]

    valid_parties: list[PartyCandidate]
    valid_obligations: list[ObligationCandidate]
    valid_payment_terms: list[PaymentTermCandidate]
    valid_clauses: list[ClauseCandidate]

    contract_metadata: ContractProviderMetadata | None

    invalid_items: list[InvalidItem]
    retry_count: int

    provider_metadata: ProviderMetadata | None

    status: AnalysisStatus
    failure_reason: str | None
    result: GenericAnalysisResult | None
    contract_result: ContractAnalysisResult | None
