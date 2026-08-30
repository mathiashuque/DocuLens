"""Repository-level PostgreSQL integration tests for `document_sections`."""

import uuid

import pytest
from app.db.repository import DocumentRepository
from app.models.document import Document
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.models import DocumentPage
from ingestion.sections import SectionCandidate


def _pages() -> list[DocumentPage]:
    return [DocumentPage(page_number=1, text="1 Top\nbody\n1.1 Child\nbody")]


def _candidates() -> list[SectionCandidate]:
    return [
        SectionCandidate(
            title="1 Top",
            level=1,
            parent_index=None,
            page_start=1,
            page_end=1,
            section_path=["1 Top"],
            text="1 Top\nbody",
        ),
        SectionCandidate(
            title="1.1 Child",
            level=2,
            parent_index=0,
            page_start=1,
            page_end=1,
            section_path=["1 Top", "1.1 Child"],
            text="1.1 Child\nbody",
        ),
    ]


@pytest.mark.asyncio
async def test_atomic_creation_maps_parent_ids_within_document(
    session: AsyncSession,
) -> None:
    repository = DocumentRepository(session)
    document = await repository.create(
        filename="doc.pdf",
        content_hash="a" * 64,
        status="parsed",
        pages=_pages(),
        sections=_candidates(),
    )
    await session.commit()

    fetched = await repository.get(document.id)

    assert fetched is not None
    assert [s.ordinal for s in fetched.sections] == [1, 2]
    assert [s.title for s in fetched.sections] == ["1 Top", "1.1 Child"]
    top, child = fetched.sections
    assert top.parent_section_id is None
    assert child.parent_section_id == top.id
    assert child.section_path == ["1 Top", "1.1 Child"]


@pytest.mark.asyncio
async def test_document_with_no_sections_persists_empty_list(
    session: AsyncSession,
) -> None:
    repository = DocumentRepository(session)
    document = await repository.create(
        filename="plain.pdf",
        content_hash="b" * 64,
        status="parsed",
        pages=[DocumentPage(page_number=1, text="no headings here")],
    )
    await session.commit()

    fetched = await repository.get(document.id)

    assert fetched is not None
    assert fetched.sections == []


@pytest.mark.asyncio
async def test_invalid_page_range_is_rejected_by_database(
    session: AsyncSession,
) -> None:
    repository = DocumentRepository(session)
    bad_candidate = _candidates()[0].model_copy(update={"page_start": 3, "page_end": 1})

    with pytest.raises(IntegrityError):
        await repository.create(
            filename="bad.pdf",
            content_hash="c" * 64,
            status="parsed",
            pages=_pages(),
            sections=[bad_candidate],
        )
    await session.rollback()

    result = await session.execute(select(Document))
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_transaction_rollback_leaves_no_partial_rows(
    session: AsyncSession,
) -> None:
    repository = DocumentRepository(session)
    candidates = _candidates()
    candidates[1] = candidates[1].model_copy(update={"level": 0})

    with pytest.raises(IntegrityError):
        await repository.create(
            filename="bad.pdf",
            content_hash="d" * 64,
            status="parsed",
            pages=_pages(),
            sections=candidates,
        )
    await session.rollback()

    result = await session.execute(select(Document))
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_document_deletion_cascades_to_sections(session: AsyncSession) -> None:
    repository = DocumentRepository(session)
    document = await repository.create(
        filename="doc.pdf",
        content_hash="e" * 64,
        status="parsed",
        pages=_pages(),
        sections=_candidates(),
    )
    await session.commit()
    document_id = document.id

    persisted = await session.get(Document, document_id)
    assert persisted is not None
    await session.delete(persisted)
    await session.commit()

    from sqlalchemy import text

    remaining = await session.execute(
        text("SELECT count(*) FROM document_sections WHERE document_id = :id"),
        {"id": document_id},
    )
    assert remaining.scalar_one() == 0


@pytest.mark.asyncio
async def test_unknown_document_returns_none(session: AsyncSession) -> None:
    repository = DocumentRepository(session)

    assert await repository.get(uuid.uuid4()) is None
