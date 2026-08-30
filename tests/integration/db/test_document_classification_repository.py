"""Repository-level PostgreSQL integration tests for classification
persistence: constraints, idempotency lookup, and evidence round trip."""

import uuid

import pytest
from app.db.classification_repository import ClassificationRepository
from app.db.repository import DocumentRepository
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.models import DocumentPage


async def _seed_document(session: AsyncSession) -> uuid.UUID:
    document = await DocumentRepository(session).create(
        filename="agreement.pdf",
        content_hash="a" * 64,
        status="parsed",
        pages=[DocumentPage(page_number=1, text="This Agreement is entered into.")],
    )
    await session.commit()
    return document.id


@pytest.mark.asyncio
async def test_create_and_get_latest_completed_round_trips_evidence(
    session: AsyncSession,
) -> None:
    document_id = await _seed_document(session)
    repository = ClassificationRepository(session)

    created = await repository.create(
        document_id=document_id,
        document_type="contract",
        confidence=0.91,
        reason="Defines parties and obligations.",
        evidence=[{"page": 1, "text": "This Agreement is entered into"}],
        provider="openai",
        model="gpt-4o-mini",
        latency_ms=120,
        input_tokens=200,
        output_tokens=40,
    )
    await session.commit()

    fetched = await repository.get_latest_completed(document_id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.document_type == "contract"
    assert fetched.evidence == [{"page": 1, "text": "This Agreement is entered into"}]
    assert fetched.status == "completed"


@pytest.mark.asyncio
async def test_unknown_document_returns_none(session: AsyncSession) -> None:
    repository = ClassificationRepository(session)

    assert await repository.get_latest_completed(uuid.uuid4()) is None


@pytest.mark.asyncio
async def test_second_classification_for_same_document_violates_unique_constraint(
    session: AsyncSession,
) -> None:
    document_id = await _seed_document(session)
    repository = ClassificationRepository(session)
    await repository.create(
        document_id=document_id,
        document_type="contract",
        confidence=0.9,
        reason="first",
        evidence=[{"page": 1, "text": "quote"}],
        provider="openai",
        model="gpt-4o-mini",
        latency_ms=None,
        input_tokens=None,
        output_tokens=None,
    )
    await session.commit()

    with pytest.raises(IntegrityError):
        await repository.create(
            document_id=document_id,
            document_type="generic",
            confidence=0.5,
            reason="second",
            evidence=[{"page": 1, "text": "quote"}],
            provider="openai",
            model="gpt-4o-mini",
            latency_ms=None,
            input_tokens=None,
            output_tokens=None,
        )
    await session.rollback()


@pytest.mark.asyncio
async def test_out_of_range_confidence_is_rejected_by_database(
    session: AsyncSession,
) -> None:
    document_id = await _seed_document(session)
    repository = ClassificationRepository(session)

    with pytest.raises(IntegrityError):
        await repository.create(
            document_id=document_id,
            document_type="contract",
            confidence=1.5,
            reason="bad",
            evidence=[{"page": 1, "text": "quote"}],
            provider="openai",
            model="gpt-4o-mini",
            latency_ms=None,
            input_tokens=None,
            output_tokens=None,
        )
    await session.rollback()


@pytest.mark.asyncio
async def test_invalid_document_type_is_rejected_by_database(
    session: AsyncSession,
) -> None:
    document_id = await _seed_document(session)
    repository = ClassificationRepository(session)

    with pytest.raises(IntegrityError):
        await repository.create(
            document_id=document_id,
            document_type="invoice",
            confidence=0.9,
            reason="bad",
            evidence=[{"page": 1, "text": "quote"}],
            provider="openai",
            model="gpt-4o-mini",
            latency_ms=None,
            input_tokens=None,
            output_tokens=None,
        )
    await session.rollback()


@pytest.mark.asyncio
async def test_deleting_document_cascades_to_classification(
    session: AsyncSession,
) -> None:
    document_id = await _seed_document(session)
    repository = ClassificationRepository(session)
    await repository.create(
        document_id=document_id,
        document_type="contract",
        confidence=0.9,
        reason="ok",
        evidence=[{"page": 1, "text": "quote"}],
        provider="openai",
        model="gpt-4o-mini",
        latency_ms=None,
        input_tokens=None,
        output_tokens=None,
    )
    await session.commit()

    document = await DocumentRepository(session).get(document_id)
    assert document is not None
    await session.delete(document)
    await session.commit()

    assert await repository.get_latest_completed(document_id) is None
