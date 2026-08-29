"""Query boundary for the `document_indexes` / `document_chunks` aggregate.

Only a `completed` index with every chunk row present is ever returned as
existing; the index and its chunks are inserted in one flush so no partial
index is ever visible to a concurrent reader.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.retrieval import DocumentChunk, DocumentIndex
from retrieval.chunking import Chunk


class DuplicateIndexError(Exception):
    """A concurrent request already created a completed index for this
    document. The caller should re-read the now-existing index rather than
    treating this as a failure."""


class RetrievalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_completed_index(self, document_id: uuid.UUID) -> DocumentIndex | None:
        statement = select(DocumentIndex).where(
            DocumentIndex.document_id == document_id,
            DocumentIndex.status == "completed",
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create_index(
        self,
        *,
        document_id: uuid.UUID,
        chunker_version: str,
        chunking_config: str,
        embedding_provider: str,
        embedding_model: str,
        dimension: int,
        chunks: list[Chunk],
        vectors: list[list[float]],
    ) -> DocumentIndex:
        """Persist one completed index and all of its chunks atomically.

        Raises `DuplicateIndexError` if a concurrent request already
        created a completed index for this document (enforced by the
        database's unique constraint, not a process-local lock).
        """
        index = DocumentIndex(
            id=uuid.uuid4(),
            document_id=document_id,
            status="completed",
            chunker_version=chunker_version,
            chunking_config=chunking_config,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            dimension=dimension,
            chunk_count=len(chunks),
            chunks=[
                DocumentChunk(
                    id=chunk.id,
                    document_id=document_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    section_id=chunk.section_id,
                    section_title=chunk.section_title,
                    section_path=chunk.section_path,
                    token_estimate=chunk.token_estimate,
                    embedding=vector,
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            ],
        )
        try:
            async with self._session.begin_nested():
                self._session.add(index)
                await self._session.flush()
        except IntegrityError as exc:
            # A SAVEPOINT confines the rollback to this insert, leaving the
            # request's outer transaction (owned by the session boundary,
            # e.g. `get_session`) usable for the caller's follow-up read of
            # the now-existing index. Only the document-uniqueness
            # violation means "a concurrent request already indexed this
            # document"; any other constraint violation (malformed chunk
            # data) is a real failure the caller must not paper over.
            if "uq_document_indexes_document_id" in str(exc.orig):
                raise DuplicateIndexError(str(document_id)) from exc
            raise
        await self._session.refresh(index, attribute_names=["created_at"])
        return index

    async def search(
        self, *, document_id: uuid.UUID, query_vector: list[float], top_k: int
    ) -> list[tuple[DocumentChunk, float]]:
        """Return the top-k chunks for `document_id` ranked by cosine
        similarity (descending), tie-broken by `chunk_index` ascending.

        `cosine_distance` is 1 - cosine_similarity, so similarity is
        derived as `1 - distance` for the response's documented `score`.
        Always scoped by `document_id` before ordering or limiting.
        """
        distance = DocumentChunk.embedding.cosine_distance(query_vector)
        statement = (
            select(DocumentChunk, distance.label("distance"))
            .where(DocumentChunk.document_id == document_id)
            .order_by(distance.asc(), DocumentChunk.chunk_index.asc())
            .limit(top_k)
        )
        result = await self._session.execute(statement)
        return [(row[0], 1.0 - row[1]) for row in result.all()]
