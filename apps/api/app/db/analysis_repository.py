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
from agent.extractors.contract.result import ContractAnalysisResult
from agent.extractors.technical_spec.result import TechnicalSpecAnalysisResult
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
    TechnicalConstraint,
    TechnicalDependency,
    TechnicalRequirement,
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
                selectinload(DocumentAnalysis.technical_requirements),
                selectinload(DocumentAnalysis.technical_constraints),
                selectinload(DocumentAnalysis.technical_dependencies),
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
        contract_specialized = (
            result.specialized
            if isinstance(result.specialized, ContractAnalysisResult)
            else None
        )
        technical_spec_specialized = (
            result.specialized
            if isinstance(result.specialized, TechnicalSpecAnalysisResult)
            else None
        )
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
                    contract_specialized.parties if contract_specialized else []
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
                    contract_specialized.obligations if contract_specialized else []
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
                    contract_specialized.payment_terms if contract_specialized else []
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
                    contract_specialized.clauses if contract_specialized else []
                )
            ],
            technical_requirements=[
                TechnicalRequirement(
                    id=requirement.id,
                    ordinal=index + 1,
                    category=requirement.category,
                    identifier=requirement.identifier,
                    statement=requirement.statement,
                    priority=requirement.priority,
                    actor=requirement.actor,
                    measurable_criterion=requirement.measurable_criterion,
                    source_page=requirement.source_page,
                    evidence=requirement.evidence,
                    confidence=requirement.confidence,
                )
                for index, requirement in enumerate(
                    technical_spec_specialized.requirements
                    if technical_spec_specialized
                    else []
                )
            ],
            technical_constraints=[
                TechnicalConstraint(
                    id=constraint.id,
                    ordinal=index + 1,
                    category=constraint.category,
                    statement=constraint.statement,
                    value_text=constraint.value_text,
                    source_page=constraint.source_page,
                    evidence=constraint.evidence,
                    confidence=constraint.confidence,
                )
                for index, constraint in enumerate(
                    technical_spec_specialized.constraints
                    if technical_spec_specialized
                    else []
                )
            ],
            technical_dependencies=[
                TechnicalDependency(
                    id=dependency.id,
                    ordinal=index + 1,
                    name=dependency.name,
                    dependency_type=dependency.dependency_type,
                    description=dependency.description,
                    source_page=dependency.source_page,
                    evidence=dependency.evidence,
                    confidence=dependency.confidence,
                )
                for index, dependency in enumerate(
                    technical_spec_specialized.dependencies
                    if technical_spec_specialized
                    else []
                )
            ],
        )
        self._session.add(analysis)
        await self._session.flush()
        await self._session.refresh(analysis, attribute_names=["created_at"])
        return analysis
