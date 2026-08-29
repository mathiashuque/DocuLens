"""Query boundary for the `document_analyses` aggregate and its child
finding/date/risk(+evidence) tables.

Only completed, evidence-validated analyses are ever inserted; the unique
`document_id` constraint makes GET's lookup a direct single-row fetch and
POST idempotent, mirroring the classification repository.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent.analysis.result import GenericAnalysisResult
from app.models.document import (
    AnalysisFinding,
    AnalysisImportantDate,
    AnalysisRisk,
    AnalysisRiskEvidence,
    ContractClause,
    ContractObligation,
    ContractParty,
    ContractPaymentTerm,
    DocumentAnalysis,
)


class AnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest_completed(
        self, document_id: uuid.UUID
    ) -> DocumentAnalysis | None:
        statement = (
            select(DocumentAnalysis)
            .where(DocumentAnalysis.document_id == document_id)
            .options(
                selectinload(DocumentAnalysis.findings),
                selectinload(DocumentAnalysis.important_dates),
                selectinload(DocumentAnalysis.risks).selectinload(
                    AnalysisRisk.evidence
                ),
                selectinload(DocumentAnalysis.contract_parties),
                selectinload(DocumentAnalysis.contract_obligations),
                selectinload(DocumentAnalysis.contract_payment_terms),
                selectinload(DocumentAnalysis.contract_clauses),
            )
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        document_id: uuid.UUID,
        document_type: str,
        extractor: str,
        result: GenericAnalysisResult,
    ) -> DocumentAnalysis:
        analysis = DocumentAnalysis(
            id=uuid.uuid4(),
            document_id=document_id,
            document_type=document_type,
            extractor=extractor,
            status="completed",
            summary_title=result.summary.title,
            summary_purpose=result.summary.purpose,
            summary_text=result.summary.summary,
            summary_key_topics=result.summary.key_topics,
            provider=result.provider,
            model=result.model,
            retry_count=result.retry_count,
            latency_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            findings=[
                AnalysisFinding(
                    id=finding.id,
                    ordinal=index + 1,
                    title=finding.title,
                    description=finding.description,
                    category=finding.category,
                    importance=finding.importance,
                    source_page=finding.source_page,
                    evidence=finding.evidence,
                    confidence=finding.confidence,
                )
                for index, finding in enumerate(result.findings)
            ],
            important_dates=[
                AnalysisImportantDate(
                    id=date.id,
                    ordinal=index + 1,
                    label=date.label,
                    raw_value=date.raw_value,
                    normalized_date=date.normalized_date,
                    source_page=date.source_page,
                    evidence=date.evidence,
                    confidence=date.confidence,
                )
                for index, date in enumerate(result.important_dates)
            ],
            risks=[
                AnalysisRisk(
                    id=risk.id,
                    ordinal=index + 1,
                    title=risk.title,
                    description=risk.description,
                    category=risk.category,
                    severity=risk.severity,
                    confidence=risk.confidence,
                    evidence=[
                        AnalysisRiskEvidence(
                            id=uuid.uuid4(),
                            ordinal=evidence_index + 1,
                            page=evidence_item.page,
                            text=evidence_item.text,
                        )
                        for evidence_index, evidence_item in enumerate(risk.evidence)
                    ],
                )
                for index, risk in enumerate(result.risks)
            ],
            contract_parties=[
                ContractParty(
                    id=party.id,
                    ordinal=index + 1,
                    name=party.name,
                    role=party.role,
                    source_page=party.source_page,
                    evidence=party.evidence,
                    confidence=party.confidence,
                )
                for index, party in enumerate(
                    result.specialized.parties if result.specialized else []
                )
            ],
            contract_obligations=[
                ContractObligation(
                    id=obligation.id,
                    ordinal=index + 1,
                    obligated_party=obligation.obligated_party,
                    description=obligation.description,
                    beneficiary=obligation.beneficiary,
                    conditions=list(obligation.conditions),
                    source_page=obligation.source_page,
                    evidence=obligation.evidence,
                    confidence=obligation.confidence,
                )
                for index, obligation in enumerate(
                    result.specialized.obligations if result.specialized else []
                )
            ],
            contract_payment_terms=[
                ContractPaymentTerm(
                    id=term.id,
                    ordinal=index + 1,
                    payer=term.payer,
                    payee=term.payee,
                    amount_text=term.amount_text,
                    schedule_text=term.schedule_text,
                    source_page=term.source_page,
                    evidence=term.evidence,
                    confidence=term.confidence,
                )
                for index, term in enumerate(
                    result.specialized.payment_terms if result.specialized else []
                )
            ],
            contract_clauses=[
                ContractClause(
                    id=clause.id,
                    ordinal=index + 1,
                    category=clause.category,
                    title=clause.title,
                    description=clause.description,
                    conditions=list(clause.conditions),
                    notice_period_text=clause.notice_period_text,
                    source_page=clause.source_page,
                    evidence=clause.evidence,
                    confidence=clause.confidence,
                )
                for index, clause in enumerate(
                    result.specialized.clauses if result.specialized else []
                )
            ],
        )
        self._session.add(analysis)
        await self._session.flush()
        await self._session.refresh(analysis, attribute_names=["created_at"])
        return analysis
