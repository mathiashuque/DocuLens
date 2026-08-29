"""Document-scoped vector search orchestration.

Embeds the query once, validates it against the stored index's
provider/model/dimension, and returns typed ranked results with complete
provenance. Never generates prose, infers claims, or persists raw queries.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import EmbeddingSettings, load_embedding_settings
from app.db.repository import DocumentRepository
from app.db.retrieval_repository import RetrievalRepository
from app.services.quota import reserve_quota
from retrieval.embedding import EmbeddingProviderUnavailableError
from retrieval.providers.openai_provider import OpenAIEmbeddingProvider

__all__ = [
    "DEFAULT_TOP_K",
    "SEARCH_STRATEGY",
    "DocumentNotFoundError",
    "IncompatibleIndexError",
    "IndexNotFoundError",
    "InvalidQueryError",
    "SearchResultItem",
    "search_document",
]

SEARCH_STRATEGY = "vector_cosine_baseline"
DEFAULT_TOP_K = 5


class DocumentNotFoundError(Exception):
    """No document exists for the given ID."""


class IndexNotFoundError(Exception):
    """No completed index exists for this document."""


class InvalidQueryError(Exception):
    """The query is blank or exceeds the configured maximum length, or
    `top_k` is out of the configured bounds."""


class IncompatibleIndexError(Exception):
    """The stored index's provider/model/dimension does not match the
    current embedding configuration."""


@dataclass(frozen=True)
class SearchResultItem:
    chunk_id: uuid.UUID
    chunk_index: int
    text: str
    page_start: int
    page_end: int
    section_id: uuid.UUID | None
    section_title: str | None
    section_path: list[str]
    score: float


def _normalize_query(raw_query: str, settings: EmbeddingSettings) -> str:
    query = " ".join(raw_query.split())
    if not query:
        raise InvalidQueryError("Query must not be blank.")
    if len(query) > settings.max_query_chars:
        raise InvalidQueryError(
            f"Query exceeds the configured maximum of "
            f"{settings.max_query_chars} characters."
        )
    return query


def _validate_top_k(top_k: int, settings: EmbeddingSettings) -> int:
    if top_k < 1 or top_k > settings.max_top_k:
        raise InvalidQueryError(f"top_k must be between 1 and {settings.max_top_k}.")
    return top_k


async def search_document(
    document_id: uuid.UUID,
    raw_query: str,
    top_k: int,
    session: AsyncSession,
    *,
    quota_identity: str | None = None,
    charge_quota: bool = True,
) -> tuple[str, list[SearchResultItem]]:
    """Search one document's chunks. Returns `(normalized_query, results)`.

    Raises `DocumentNotFoundError`/`IndexNotFoundError` for 404s,
    `InvalidQueryError` for bad input, `IncompatibleIndexError` if the
    index predates the current embedding configuration, and the embedding
    provider's own errors (mapped to 502/503 at the route) on failure.
    """
    document = await DocumentRepository(session).get(document_id)
    if document is None:
        raise DocumentNotFoundError(str(document_id))

    retrieval_repository = RetrievalRepository(session)
    index = await retrieval_repository.get_completed_index(document_id)
    if index is None:
        raise IndexNotFoundError(str(document_id))

    settings = load_embedding_settings()
    query = _normalize_query(raw_query, settings)
    bounded_top_k = _validate_top_k(top_k, settings)

    if (
        index.embedding_provider != "openai"
        or index.embedding_model != settings.model
        or index.dimension != settings.dimension
    ):
        raise IncompatibleIndexError(
            f"Index for document {document_id} uses "
            f"{index.embedding_provider}/{index.embedding_model}"
            f"@{index.dimension}, incompatible with current configuration."
        )

    if not settings.api_key:
        raise EmbeddingProviderUnavailableError("Embedding provider is not configured.")
    provider = OpenAIEmbeddingProvider(
        api_key=settings.api_key,
        model=settings.model,
        dimension=settings.dimension,
        timeout_seconds=settings.timeout_seconds,
    )
    if charge_quota:
        await reserve_quota(
            session, quota_identity, "question", document_id=document_id
        )
    embedded_query = await provider.embed_query(query)

    rows = await retrieval_repository.search(
        document_id=document_id,
        query_vector=embedded_query.vector,
        top_k=bounded_top_k,
    )
    results = [
        SearchResultItem(
            chunk_id=chunk.id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            section_id=chunk.section_id,
            section_title=chunk.section_title,
            section_path=chunk.section_path,
            score=score,
        )
        for chunk, score in rows
    ]
    return query, results
