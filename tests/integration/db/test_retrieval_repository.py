"""Repository-level PostgreSQL/pgvector integration tests: persistence
round trip, exact cosine ranking, and strict document-scoped isolation."""

import uuid

import pytest
from app.db.repository import DocumentRepository
from app.db.retrieval_repository import DuplicateIndexError, RetrievalRepository
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.models import DocumentPage
from retrieval.chunking import Chunk

DIMENSION = 1536


def _vector(*, lead: float) -> list[float]:
    """A unit-ish vector with a distinguishing first coordinate; distinct
    `lead` values are dissimilar under cosine distance."""
    vector = [0.0] * DIMENSION
    vector[0] = lead
    vector[1] = 1.0
    return vector


async def _create_document(session: AsyncSession, *, content_hash: str) -> uuid.UUID:
    document = await DocumentRepository(session).create(
        filename="doc.pdf",
        content_hash=content_hash,
        status="parsed",
        pages=[DocumentPage(page_number=1, text="hello world")],
    )
    await session.commit()
    return document.id


def _chunk(document_id: uuid.UUID, index: int, *, text: str = "chunk text") -> Chunk:
    return Chunk(
        id=uuid.uuid4(),
        document_id=document_id,
        chunk_index=index,
        text=text,
        page_start=1,
        page_end=1,
        section_id=None,
        section_title=None,
        section_path=[],
        token_estimate=2,
    )


@pytest.mark.asyncio
async def test_create_index_persists_index_and_chunks_atomically(
    session: AsyncSession,
) -> None:
    document_id = await _create_document(session, content_hash="a" * 64)
    repository = RetrievalRepository(session)
    chunks = [_chunk(document_id, 0), _chunk(document_id, 1)]

    index = await repository.create_index(
        document_id=document_id,
        chunker_version="v1",
        chunking_config="target=800,overlap=120",
        embedding_provider="fake",
        embedding_model="fake-model",
        dimension=DIMENSION,
        chunks=chunks,
        vectors=[_vector(lead=1.0), _vector(lead=-1.0)],
    )
    await session.commit()

    assert index.chunk_count == 2
    fetched = await repository.get_completed_index(document_id)
    assert fetched is not None
    assert fetched.id == index.id


@pytest.mark.asyncio
async def test_search_ranks_by_exact_cosine_similarity_with_stable_ties(
    session: AsyncSession,
) -> None:
    document_id = await _create_document(session, content_hash="b" * 64)
    repository = RetrievalRepository(session)
    chunks = [_chunk(document_id, i) for i in range(3)]
    # chunk 0 closest to query, chunk 1 identical direction to chunk 2 (tie)
    await repository.create_index(
        document_id=document_id,
        chunker_version="v1",
        chunking_config="cfg",
        embedding_provider="fake",
        embedding_model="fake-model",
        dimension=DIMENSION,
        chunks=chunks,
        vectors=[_vector(lead=1.0), _vector(lead=0.0), _vector(lead=0.0)],
    )
    await session.commit()

    results = await repository.search(
        document_id=document_id, query_vector=_vector(lead=1.0), top_k=3
    )

    assert [c.chunk_index for c, _ in results] == [0, 1, 2]  # tie broken by index
    assert results[0][1] > results[1][1]


@pytest.mark.asyncio
async def test_search_never_leaks_across_documents(session: AsyncSession) -> None:
    doc_a = await _create_document(session, content_hash="c" * 64)
    doc_b = await _create_document(session, content_hash="d" * 64)
    repository = RetrievalRepository(session)

    # doc_b's chunk is a closer vector match than doc_a's own chunk.
    await repository.create_index(
        document_id=doc_a,
        chunker_version="v1",
        chunking_config="cfg",
        embedding_provider="fake",
        embedding_model="fake-model",
        dimension=DIMENSION,
        chunks=[_chunk(doc_a, 0)],
        vectors=[_vector(lead=-5.0)],
    )
    await repository.create_index(
        document_id=doc_b,
        chunker_version="v1",
        chunking_config="cfg",
        embedding_provider="fake",
        embedding_model="fake-model",
        dimension=DIMENSION,
        chunks=[_chunk(doc_b, 0)],
        vectors=[_vector(lead=1.0)],
    )
    await session.commit()

    results = await repository.search(
        document_id=doc_a, query_vector=_vector(lead=1.0), top_k=5
    )

    assert len(results) == 1
    assert results[0][0].document_id == doc_a


@pytest.mark.asyncio
async def test_duplicate_index_for_same_document_raises(session: AsyncSession) -> None:
    document_id = await _create_document(session, content_hash="e" * 64)
    repository = RetrievalRepository(session)
    await repository.create_index(
        document_id=document_id,
        chunker_version="v1",
        chunking_config="cfg",
        embedding_provider="fake",
        embedding_model="fake-model",
        dimension=DIMENSION,
        chunks=[_chunk(document_id, 0)],
        vectors=[_vector(lead=1.0)],
    )
    await session.commit()

    with pytest.raises(DuplicateIndexError):
        await repository.create_index(
            document_id=document_id,
            chunker_version="v1",
            chunking_config="cfg",
            embedding_provider="fake",
            embedding_model="fake-model",
            dimension=DIMENSION,
            chunks=[_chunk(document_id, 0)],
            vectors=[_vector(lead=1.0)],
        )
    # The outer transaction survives the nested-savepoint rollback.
    fetched = await repository.get_completed_index(document_id)
    assert fetched is not None


@pytest.mark.asyncio
async def test_invalid_chunk_rolls_back_entire_index(session: AsyncSession) -> None:
    document_id = await _create_document(session, content_hash="f" * 64)
    repository = RetrievalRepository(session)
    bad_chunk = _chunk(document_id, 0, text="")  # violates nonempty-text check

    with pytest.raises(IntegrityError):
        await repository.create_index(
            document_id=document_id,
            chunker_version="v1",
            chunking_config="cfg",
            embedding_provider="fake",
            embedding_model="fake-model",
            dimension=DIMENSION,
            chunks=[_chunk(document_id, 1), bad_chunk],
            vectors=[_vector(lead=1.0), _vector(lead=0.5)],
        )
    await session.rollback()

    fetched = await RetrievalRepository(session).get_completed_index(document_id)
    assert fetched is None
