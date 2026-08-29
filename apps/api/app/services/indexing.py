"""Document indexing orchestration: eligibility, idempotency, chunking,
bounded embedding, and atomic persistence.

Keeps API/service/domain/provider/repository concerns separate: this module
knows about documents and HTTP-free typed errors; `retrieval.chunking` and
`retrieval.embedding` know nothing about SQLAlchemy or FastAPI.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import EmbeddingSettings, load_embedding_settings
from app.db.repository import DocumentRepository
from app.db.retrieval_repository import DuplicateIndexError, RetrievalRepository
from app.models.document import Document
from app.models.retrieval import DocumentIndex
from ingestion.models import DocumentPage as ParsedPage
from retrieval.chunking import (
    CHUNKER_VERSION,
    DEFAULT_CHUNKING_CONFIG,
    ChunkingConfig,
    ChunkingError,
    SectionInput,
    chunk_document,
)
from retrieval.embedding import (
    EmbeddingProvider,
    EmbeddingProviderRequestError,
    EmbeddingProviderUnavailableError,
)
from retrieval.providers.openai_provider import OpenAIEmbeddingProvider

__all__ = [
    "DocumentNotFoundError",
    "EmbeddingProviderRequestError",
    "EmbeddingProviderUnavailableError",
    "IncompatibleIndexError",
    "IneligibleDocumentError",
    "index_document",
]


class DocumentNotFoundError(Exception):
    """No document exists for the given ID."""


class IneligibleDocumentError(Exception):
    """The document cannot be indexed (not `parsed`, or has no text)."""


class IncompatibleIndexError(Exception):
    """An existing index used a different provider/model/dimension than
    the current configuration. Reindexing is a later, explicit feature;
    this is reported rather than silently rebuilt."""


def _build_provider(settings: EmbeddingSettings) -> EmbeddingProvider:
    if not settings.api_key:
        raise EmbeddingProviderUnavailableError("Embedding provider is not configured.")
    return OpenAIEmbeddingProvider(
        api_key=settings.api_key,
        model=settings.model,
        dimension=settings.dimension,
        timeout_seconds=settings.timeout_seconds,
        max_batch_size=settings.max_batch_size,
    )


def _check_eligibility(document: Document) -> None:
    if document.status != "parsed":
        raise IneligibleDocumentError(
            f"Document {document.id} is not eligible for indexing "
            f"(status={document.status})."
        )
    if not any(page.text.strip() for page in document.pages):
        raise IneligibleDocumentError(f"Document {document.id} has no text to index.")


def _check_compatible(existing: DocumentIndex, settings: EmbeddingSettings) -> None:
    if (
        existing.embedding_provider != "openai"
        or existing.embedding_model != settings.model
        or existing.dimension != settings.dimension
    ):
        raise IncompatibleIndexError(
            f"Existing index for document {existing.document_id} uses "
            f"{existing.embedding_provider}/{existing.embedding_model}"
            f"@{existing.dimension}, which does not match current "
            f"configuration."
        )


async def index_document(
    document_id: uuid.UUID,
    session: AsyncSession,
    *,
    chunking_config: ChunkingConfig = DEFAULT_CHUNKING_CONFIG,
    embed_batch_size: int = 96,
) -> tuple[DocumentIndex, bool]:
    """Index `document_id`, or return its existing compatible index.

    Returns `(index, created)`; `created` is False when an existing
    completed, compatible index already satisfied the request without
    building a provider or making a paid call.
    """
    document = await DocumentRepository(session).get(document_id)
    if document is None:
        raise DocumentNotFoundError(str(document_id))

    retrieval_repository = RetrievalRepository(session)
    existing = await retrieval_repository.get_completed_index(document_id)
    settings = load_embedding_settings()
    if existing is not None:
        _check_compatible(existing, settings)
        return existing, False

    _check_eligibility(document)

    try:
        sections = [
            SectionInput(
                id=section.id,
                title=section.title,
                page_start=section.page_start,
                page_end=section.page_end,
                section_path=section.section_path,
                level=section.level,
            )
            for section in document.sections
        ]
        chunks = chunk_document(
            document_id=document_id,
            pages=[
                ParsedPage(page_number=p.page_number, text=p.text)
                for p in document.pages
            ],
            sections=sections,
            config=chunking_config,
        )
    except ChunkingError as exc:
        raise IneligibleDocumentError(str(exc)) from exc

    provider = _build_provider(settings)

    vectors: list[list[float]] = []
    for start in range(0, len(chunks), embed_batch_size):
        batch = chunks[start : start + embed_batch_size]
        result = await provider.embed_documents([c.text for c in batch])
        vectors.extend(result.vectors)

    try:
        index = await retrieval_repository.create_index(
            document_id=document_id,
            chunker_version=CHUNKER_VERSION,
            chunking_config=chunking_config.config_id,
            embedding_provider="openai",
            embedding_model=settings.model,
            dimension=settings.dimension,
            chunks=chunks,
            vectors=vectors,
        )
    except DuplicateIndexError:
        existing = await retrieval_repository.get_completed_index(document_id)
        if existing is None:  # pragma: no cover - defensive; DB guarantees this
            raise
        _check_compatible(existing, settings)
        return existing, False

    return index, True
