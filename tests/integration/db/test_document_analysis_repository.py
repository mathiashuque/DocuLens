"""Repository-level PostgreSQL integration tests for analysis persistence:
constraints, idempotency lookup, ordering, and full provenance round trip."""

import uuid

import pytest
from app.db.analysis_repository import AnalysisRepository
from app.db.repository import DocumentRepository
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agent.analysis.result import (
    FindingResult,
    GenericAnalysisResult,
    ImportantDateResult,
    RiskEvidenceResult,
    RiskResult,
)
from agent.analysis.types import DocumentSummaryCandidate
from ingestion.models import DocumentPage


async def _seed_document(session: AsyncSession) -> uuid.UUID:
    document = await DocumentRepository(session).create(
        filename="memo.pdf",
        content_hash="a" * 64,
        status="parsed",
        pages=[DocumentPage(page_number=1, text="The term renews automatically.")],
    )
    await session.commit()
    return document.id


def _result(**overrides: object) -> GenericAnalysisResult:
    base: dict[str, object] = {
        "summary": DocumentSummaryCandidate(
            title="Memo", purpose="p", summary="s", key_topics=["renewal"]
        ),
        "findings": (
            FindingResult(
                id=uuid.uuid4(),
                title="Auto-renewal",
                description="d",
                category="renewal",
                importance="high",
                source_page=1,
                evidence="renews automatically",
                confidence=0.9,
            ),
        ),
        "important_dates": (
            ImportantDateResult(
                id=uuid.uuid4(),
                label="Renewal",
                raw_value="soon",
                normalized_date=None,
                source_page=1,
                evidence="renews automatically",
                confidence=0.5,
            ),
        ),
        "risks": (
            RiskResult(
                id=uuid.uuid4(),
                title="Auto-renewal risk",
                description="d",
                category="renewal",
                severity="medium",
                evidence=(RiskEvidenceResult(page=1, text="renews automatically"),),
                confidence=0.6,
            ),
        ),
        "provider": "openai",
        "model": "gpt-4o-mini",
        "latency_ms": 250,
        "input_tokens": 900,
        "output_tokens": 200,
        "retry_count": 0,
    }
    base.update(overrides)
    return GenericAnalysisResult(**base)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_create_and_get_latest_completed_round_trips_full_provenance(
    session: AsyncSession,
) -> None:
    document_id = await _seed_document(session)
    repository = AnalysisRepository(session)

    created = await repository.create(
        document_id=document_id,
        document_type="generic",
        extractor="generic",
        result=_result(),
    )
    await session.commit()

    fetched = await repository.get_latest_completed(document_id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.summary_purpose == "p"
    assert fetched.summary_key_topics == ["renewal"]
    assert len(fetched.findings) == 1
    assert fetched.findings[0].evidence == "renews automatically"
    assert len(fetched.important_dates) == 1
    assert fetched.important_dates[0].normalized_date is None
    assert len(fetched.risks) == 1
    assert len(fetched.risks[0].evidence) == 1
    assert fetched.risks[0].evidence[0].page == 1
    assert fetched.status == "completed"


@pytest.mark.asyncio
async def test_unknown_document_returns_none(session: AsyncSession) -> None:
    repository = AnalysisRepository(session)

    assert await repository.get_latest_completed(uuid.uuid4()) is None


@pytest.mark.asyncio
async def test_second_analysis_for_same_document_violates_unique_constraint(
    session: AsyncSession,
) -> None:
    document_id = await _seed_document(session)
    repository = AnalysisRepository(session)
    await repository.create(
        document_id=document_id,
        document_type="generic",
        extractor="generic",
        result=_result(),
    )
    await session.commit()

    with pytest.raises(IntegrityError):
        await repository.create(
            document_id=document_id,
            document_type="generic",
            extractor="generic",
            result=_result(),
        )
    await session.rollback()


@pytest.mark.asyncio
async def test_empty_findings_dates_risks_persist_as_empty_lists(
    session: AsyncSession,
) -> None:
    document_id = await _seed_document(session)
    repository = AnalysisRepository(session)

    await repository.create(
        document_id=document_id,
        document_type="generic",
        extractor="generic",
        result=_result(findings=(), important_dates=(), risks=()),
    )
    await session.commit()

    fetched = await repository.get_latest_completed(document_id)

    assert fetched is not None
    assert fetched.findings == []
    assert fetched.important_dates == []
    assert fetched.risks == []


@pytest.mark.asyncio
async def test_invalid_document_type_is_rejected_by_database(
    session: AsyncSession,
) -> None:
    document_id = await _seed_document(session)
    repository = AnalysisRepository(session)

    with pytest.raises(IntegrityError):
        await repository.create(
            document_id=document_id,
            document_type="invoice",
            extractor="generic",
            result=_result(),
        )
    await session.rollback()


@pytest.mark.asyncio
async def test_deleting_document_cascades_to_analysis_and_children(
    session: AsyncSession,
) -> None:
    document_id = await _seed_document(session)
    repository = AnalysisRepository(session)
    await repository.create(
        document_id=document_id,
        document_type="generic",
        extractor="generic",
        result=_result(),
    )
    await session.commit()

    document = await DocumentRepository(session).get(document_id)
    assert document is not None
    await session.delete(document)
    await session.commit()

    assert await repository.get_latest_completed(document_id) is None
