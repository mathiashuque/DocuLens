"""Public generic analysis API response contract.

AI-generated interpretation is labeled as such through this contract's own
shape (`summary` is clearly the model's interpretation; findings/dates/risks
each carry their own page/evidence provenance) rather than through prose.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from agent.classification.taxonomy import DocumentType


class AnalysisSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str | None
    purpose: str
    summary: str
    key_topics: list[str]


class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    category: str
    importance: Literal["low", "medium", "high", "critical"]
    source_page: int
    evidence: str
    confidence: float


class ImportantDateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    raw_value: str
    normalized_date: str | None
    source_page: int
    evidence: str
    confidence: float


class RiskEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page: int
    text: str


class RiskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    category: str
    severity: Literal["low", "medium", "high", "critical"]
    evidence: list[RiskEvidenceResponse]
    confidence: float


class PartyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    role: str | None
    source_page: int
    evidence: str
    confidence: float


class ObligationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    obligated_party: str | None
    description: str
    beneficiary: str | None
    conditions: list[str]
    source_page: int
    evidence: str
    confidence: float


class PaymentTermResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payer: str | None
    payee: str | None
    amount_text: str | None
    schedule_text: str | None
    source_page: int
    evidence: str
    confidence: float


class ClauseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    conditions: list[str]
    notice_period_text: str | None
    source_page: int
    evidence: str
    confidence: float


class ContractAnalysisResponse(BaseModel):
    type: Literal["contract"] = "contract"
    extractor: Literal["contract_terms"] = "contract_terms"
    parties: list[PartyResponse]
    obligations: list[ObligationResponse]
    payment_terms: list[PaymentTermResponse]
    renewal_terms: list[ClauseResponse]
    termination_terms: list[ClauseResponse]
    liability_terms: list[ClauseResponse]
    confidentiality_terms: list[ClauseResponse]


class AnalysisResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    document_type: DocumentType
    extractor: Literal["generic", "contract_terms"]
    status: Literal["completed"]
    summary: AnalysisSummaryResponse
    findings: list[FindingResponse]
    important_dates: list[ImportantDateResponse]
    risks: list[RiskResponse]
    specialized_analysis: ContractAnalysisResponse | None = None
    provider: str
    model: str
    created_at: datetime

    @classmethod
    def from_analysis(cls, analysis: object) -> "AnalysisResponse":
        """Build the response from a `DocumentAnalysis` ORM row.

        A plain `model_validate(..., from_attributes=True)` cannot map the
        row's flat `summary_*` columns onto the nested `summary` object, so
        this assembles it explicitly. `specialized_analysis` is populated
        only when the row's `extractor` is `contract_terms`; other
        classifications never carry contract child rows.
        """
        specialized_analysis = None
        if analysis.extractor == "contract_terms":  # type: ignore[attr-defined]
            clauses = list(analysis.contract_clauses)  # type: ignore[attr-defined]
            specialized_analysis = ContractAnalysisResponse(
                parties=[
                    PartyResponse.model_validate(party)
                    for party in analysis.contract_parties  # type: ignore[attr-defined]
                ],
                obligations=[
                    ObligationResponse.model_validate(obligation)
                    for obligation in analysis.contract_obligations  # type: ignore[attr-defined]
                ],
                payment_terms=[
                    PaymentTermResponse.model_validate(term)
                    for term in analysis.contract_payment_terms  # type: ignore[attr-defined]
                ],
                renewal_terms=[
                    ClauseResponse.model_validate(clause)
                    for clause in clauses
                    if clause.category == "renewal"
                ],
                termination_terms=[
                    ClauseResponse.model_validate(clause)
                    for clause in clauses
                    if clause.category == "termination"
                ],
                liability_terms=[
                    ClauseResponse.model_validate(clause)
                    for clause in clauses
                    if clause.category == "liability"
                ],
                confidentiality_terms=[
                    ClauseResponse.model_validate(clause)
                    for clause in clauses
                    if clause.category == "confidentiality"
                ],
            )

        return cls(
            id=analysis.id,  # type: ignore[attr-defined]
            document_id=analysis.document_id,  # type: ignore[attr-defined]
            document_type=analysis.document_type,  # type: ignore[attr-defined]
            extractor=analysis.extractor,  # type: ignore[attr-defined]
            status=analysis.status,  # type: ignore[attr-defined]
            summary=AnalysisSummaryResponse(
                title=analysis.summary_title,  # type: ignore[attr-defined]
                purpose=analysis.summary_purpose,  # type: ignore[attr-defined]
                summary=analysis.summary_text,  # type: ignore[attr-defined]
                key_topics=analysis.summary_key_topics,  # type: ignore[attr-defined]
            ),
            findings=[
                FindingResponse.model_validate(finding)
                for finding in analysis.findings  # type: ignore[attr-defined]
            ],
            important_dates=[
                ImportantDateResponse.model_validate(date)
                for date in analysis.important_dates  # type: ignore[attr-defined]
            ],
            risks=[
                RiskResponse.model_validate(risk)
                for risk in analysis.risks  # type: ignore[attr-defined]
            ],
            specialized_analysis=specialized_analysis,
            provider=analysis.provider,  # type: ignore[attr-defined]
            model=analysis.model,  # type: ignore[attr-defined]
            created_at=analysis.created_at,  # type: ignore[attr-defined]
        )
