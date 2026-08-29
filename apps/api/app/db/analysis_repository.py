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
        )
        self._session.add(analysis)
        await self._session.flush()
        await self._session.refresh(analysis, attribute_names=["created_at"])
        return analysis
