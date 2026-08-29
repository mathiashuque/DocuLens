"""Repository-level PostgreSQL integration tests: ordering, invariants, atomicity."""

import uuid

import pytest
from app.db.repository import DocumentRepository
from app.models.document import Document
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.models import DocumentPage


@pytest.mark.asyncio
async def test_create_and_get_two_page_document_preserves_order(
    session: AsyncSession,
) -> None:
    repository = DocumentRepository(session)
    document = await repository.create(
        filename="example.pdf",
        content_hash="a" * 64,
        status="parsed",
        pages=[
            DocumentPage(page_number=1, text="First page text"),
            DocumentPage(page_number=2, text="Second page text"),
        ],
    )
    await session.commit()

    fetched = await repository.get(document.id)

    assert fetched is not None
    assert fetched.filename == "example.pdf"
    assert fetched.page_count == 2
    assert [page.page_number for page in fetched.pages] == [1, 2]
    assert fetched.pages[0].text == "First page text"
    assert fetched.pages[1].text == "Second page text"


@pytest.mark.asyncio
async def test_blank_page_is_preserved(session: AsyncSession) -> None:
    repository = DocumentRepository(session)
    document = await repository.create(
        filename="scan.pdf",
        content_hash="b" * 64,
        status="ocr_required",
        pages=[
            DocumentPage(page_number=1, text="Some text"),
            DocumentPage(page_number=2, text=""),
        ],
    )
    await session.commit()

    fetched = await repository.get(document.id)

    assert fetched is not None
    assert fetched.pages[1].page_number == 2
    assert fetched.pages[1].text == ""


@pytest.mark.asyncio
async def test_ocr_required_status_persists(session: AsyncSession) -> None:
    repository = DocumentRepository(session)
    document = await repository.create(
        filename="scan.pdf",
        content_hash="c" * 64,
        status="ocr_required",
        pages=[DocumentPage(page_number=1, text="")],
    )
    await session.commit()

    fetched = await repository.get(document.id)

    assert fetched is not None
    assert fetched.status == "ocr_required"


@pytest.mark.asyncio
async def test_unknown_id_returns_none(session: AsyncSession) -> None:
    repository = DocumentRepository(session)

    assert await repository.get(uuid.uuid4()) is None


@pytest.mark.asyncio
async def test_duplicate_page_number_fails_atomically(session: AsyncSession) -> None:
    repository = DocumentRepository(session)

    with pytest.raises(IntegrityError):
        await repository.create(
            filename="bad.pdf",
            content_hash="d" * 64,
            status="parsed",
            pages=[
                DocumentPage(page_number=1, text="a"),
                DocumentPage(page_number=1, text="b"),
            ],
        )
    await session.rollback()

    result = await session.execute(select(Document))
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_invalid_page_number_is_rejected_by_database(
    session: AsyncSession,
) -> None:
    repository = DocumentRepository(session)

    with pytest.raises(IntegrityError):
        await repository.create(
            filename="bad.pdf",
            content_hash="e" * 64,
            status="parsed",
            pages=[DocumentPage(page_number=0, text="a")],
        )
    await session.rollback()


@pytest.mark.asyncio
async def test_zero_pages_violates_page_count_constraint(session: AsyncSession) -> None:
    repository = DocumentRepository(session)

    with pytest.raises(IntegrityError):
        await repository.create(
            filename="empty.pdf",
            content_hash="f" * 64,
            status="parsed",
            pages=[],
        )
    await session.rollback()


@pytest.mark.asyncio
async def test_invalid_content_hash_is_rejected_by_database(
    session: AsyncSession,
) -> None:
    repository = DocumentRepository(session)

    with pytest.raises(IntegrityError):
        await repository.create(
            filename="bad.pdf",
            content_hash="not-a-sha256-hash",
            status="parsed",
            pages=[DocumentPage(page_number=1, text="a")],
        )
    await session.rollback()
