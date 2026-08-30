"""Final, app-ID-assigned contract extraction result.

IDs are generated here, in application code — never trusted from the
provider. Mirrors `agent.analysis.result`.
"""

import uuid
from dataclasses import dataclass, field

from agent.extractors.contract.provider import ProviderMetadata
from agent.extractors.contract.taxonomy import CONTRACT_EXTRACTOR
from agent.extractors.contract.types import (
    ClauseCandidate,
    ObligationCandidate,
    PartyCandidate,
    PaymentTermCandidate,
)


@dataclass(frozen=True)
class PartyResult:
    id: uuid.UUID
    name: str
    role: str | None
    source_page: int
    evidence: str
    confidence: float


@dataclass(frozen=True)
class ObligationResult:
    id: uuid.UUID
    obligated_party: str | None
    description: str
    beneficiary: str | None
    conditions: tuple[str, ...]
    source_page: int
    evidence: str
    confidence: float


@dataclass(frozen=True)
class PaymentTermResult:
    id: uuid.UUID
    payer: str | None
    payee: str | None
    amount_text: str | None
    schedule_text: str | None
    source_page: int
    evidence: str
    confidence: float


@dataclass(frozen=True)
class ClauseResult:
    id: uuid.UUID
    category: str
    title: str
    description: str
    conditions: tuple[str, ...]
    notice_period_text: str | None
    source_page: int
    evidence: str
    confidence: float


@dataclass(frozen=True)
class ContractAnalysisResult:
    extractor: str = CONTRACT_EXTRACTOR
    parties: tuple[PartyResult, ...] = field(default_factory=tuple)
    obligations: tuple[ObligationResult, ...] = field(default_factory=tuple)
    payment_terms: tuple[PaymentTermResult, ...] = field(default_factory=tuple)
    clauses: tuple[ClauseResult, ...] = field(default_factory=tuple)
    provider: str = ""
    model: str = ""
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None

    @property
    def renewal_terms(self) -> tuple[ClauseResult, ...]:
        return tuple(c for c in self.clauses if c.category == "renewal")

    @property
    def termination_terms(self) -> tuple[ClauseResult, ...]:
        return tuple(c for c in self.clauses if c.category == "termination")

    @property
    def liability_terms(self) -> tuple[ClauseResult, ...]:
        return tuple(c for c in self.clauses if c.category == "liability")

    @property
    def confidentiality_terms(self) -> tuple[ClauseResult, ...]:
        return tuple(c for c in self.clauses if c.category == "confidentiality")


def assign_contract_ids(
    *,
    parties: list[PartyCandidate],
    obligations: list[ObligationCandidate],
    payment_terms: list[PaymentTermCandidate],
    clauses: list[ClauseCandidate],
    metadata: ProviderMetadata,
) -> ContractAnalysisResult:
    return ContractAnalysisResult(
        parties=tuple(
            PartyResult(
                id=uuid.uuid4(),
                name=item.name,
                role=item.role,
                source_page=item.source_page,
                evidence=item.evidence,
                confidence=item.confidence,
            )
            for item in parties
        ),
        obligations=tuple(
            ObligationResult(
                id=uuid.uuid4(),
                obligated_party=item.obligated_party,
                description=item.description,
                beneficiary=item.beneficiary,
                conditions=tuple(item.conditions),
                source_page=item.source_page,
                evidence=item.evidence,
                confidence=item.confidence,
            )
            for item in obligations
        ),
        payment_terms=tuple(
            PaymentTermResult(
                id=uuid.uuid4(),
                payer=item.payer,
                payee=item.payee,
                amount_text=item.amount_text,
                schedule_text=item.schedule_text,
                source_page=item.source_page,
                evidence=item.evidence,
                confidence=item.confidence,
            )
            for item in payment_terms
        ),
        clauses=tuple(
            ClauseResult(
                id=uuid.uuid4(),
                category=item.category,
                title=item.title,
                description=item.description,
                conditions=tuple(item.conditions),
                notice_period_text=item.notice_period_text,
                source_page=item.source_page,
                evidence=item.evidence,
                confidence=item.confidence,
            )
            for item in clauses
        ),
        provider=metadata.provider,
        model=metadata.model,
        latency_ms=metadata.latency_ms,
        input_tokens=metadata.input_tokens,
        output_tokens=metadata.output_tokens,
    )
