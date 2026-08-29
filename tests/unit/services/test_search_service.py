"""Service-level search tests using fakes for the repository and
embedding-provider boundaries; no database or network required.

Covers: unknown document/index 404s, blank/oversized query and top_k
bounds, incompatible index detection, missing-provider mapping, and a
single query-embedding call that is scoped to the requested document.
"""

import uuid
from typing import Any

import pytest
from app.services.search import (
    DocumentNotFoundError,
    IncompatibleIndexError,
    IndexNotFoundError,
    InvalidQueryError,
    search_document,
)

from retrieval.embedding import EmbeddingProviderUnavailableError


class _FakeDocument:
    def __init__(self, document_id: uuid.UUID) -> None:
        self.id = document_id


class _FakeDocumentRepository:
    def __init__(self, document: _FakeDocument | None) -> None:
        self._document = document

    def __call__(self, _session: Any) -> "_FakeDocumentRepository":
        return self

    async def get(self, _document_id: uuid.UUID):
        return self._document


class _FakeIndex:
    def __init__(
        self,
        *,
        embedding_provider: str = "openai",
        embedding_model: str = "text-embedding-3-small",
        dimension: int = 1536,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.dimension = dimension


class _FakeChunk:
    def __init__(self, chunk_index: int) -> None:
        self.id = uuid.uuid4()
        self.chunk_index = chunk_index
        self.text = f"chunk {chunk_index} text"
        self.page_start = 1
        self.page_end = 1
        self.section_id = None
        self.section_title = None
        self.section_path: list[str] = []


class _FakeRetrievalRepository:
    def __init__(self, index: _FakeIndex | None, rows: list[tuple[Any, float]]) -> None:
        self.index = index
        self.rows = rows
        self.search_calls: list[dict[str, Any]] = []

    def __call__(self, _session: Any) -> "_FakeRetrievalRepository":
        return self

    async def get_completed_index(self, _document_id: uuid.UUID):
        return self.index

    async def search(self, **kwargs: Any):
        self.search_calls.append(kwargs)
        return self.rows


class _Settings:
    api_key: str | None = "key"
    model = "text-embedding-3-small"
    dimension = 1536
    timeout_seconds = 1.0
    max_query_chars = 20
    max_top_k = 5


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    *,
    document: _FakeDocument | None,
    index: _FakeIndex | None,
    rows: list[tuple[Any, float]] | None = None,
    settings: _Settings | None = None,
) -> _FakeRetrievalRepository:
    retrieval_repo = _FakeRetrievalRepository(index, rows or [])
    monkeypatch.setattr(
        "app.services.search.DocumentRepository", _FakeDocumentRepository(document)
    )
    monkeypatch.setattr("app.services.search.RetrievalRepository", retrieval_repo)
    monkeypatch.setattr(
        "app.services.search.load_embedding_settings", lambda: settings or _Settings()
    )
    return retrieval_repo


@pytest.mark.asyncio
async def test_unknown_document_raises_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch(monkeypatch, document=None, index=None)
    with pytest.raises(DocumentNotFoundError):
        await search_document(uuid.uuid4(), "hello", 5, session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_missing_index_raises_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    document_id = uuid.uuid4()
    _patch(monkeypatch, document=_FakeDocument(document_id), index=None)
    with pytest.raises(IndexNotFoundError):
        await search_document(document_id, "hello", 5, session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_blank_query_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    document_id = uuid.uuid4()
    _patch(monkeypatch, document=_FakeDocument(document_id), index=_FakeIndex())
    with pytest.raises(InvalidQueryError):
        await search_document(document_id, "   ", 5, session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_oversized_query_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    document_id = uuid.uuid4()
    _patch(monkeypatch, document=_FakeDocument(document_id), index=_FakeIndex())
    with pytest.raises(InvalidQueryError):
        await search_document(
            document_id,
            "x" * 100,
            5,
            session=object(),  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_top_k_out_of_bounds_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    document_id = uuid.uuid4()
    _patch(monkeypatch, document=_FakeDocument(document_id), index=_FakeIndex())
    with pytest.raises(InvalidQueryError):
        await search_document(document_id, "hello", 0, session=object())  # type: ignore[arg-type]
    with pytest.raises(InvalidQueryError):
        await search_document(document_id, "hello", 999, session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_incompatible_index_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    document_id = uuid.uuid4()
    _patch(
        monkeypatch,
        document=_FakeDocument(document_id),
        index=_FakeIndex(embedding_model="text-embedding-3-large"),
    )
    with pytest.raises(IncompatibleIndexError):
        await search_document(document_id, "hello", 5, session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_missing_api_key_maps_to_provider_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    no_key_settings = _Settings()
    no_key_settings.api_key = None
    _patch(
        monkeypatch,
        document=_FakeDocument(document_id),
        index=_FakeIndex(),
        settings=no_key_settings,
    )
    with pytest.raises(EmbeddingProviderUnavailableError):
        await search_document(document_id, "hello", 5, session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_normalizes_whitespace_scopes_by_document_and_embeds_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    chunk = _FakeChunk(0)
    retrieval_repo = _patch(
        monkeypatch,
        document=_FakeDocument(document_id),
        index=_FakeIndex(dimension=4, embedding_model="fake-model"),
        rows=[(chunk, 0.9)],
        settings=_Settings(),
    )
    retrieval_repo.index.embedding_model = "fake-model"
    retrieval_repo.index.dimension = 4

    call_count = 0

    class _FakeQueryProvider:
        async def embed_query(self, text: str):
            nonlocal call_count
            call_count += 1
            from retrieval.embedding import EmbeddingVector

            assert text == "hello world"  # normalized from extra whitespace
            return EmbeddingVector(
                vector=[0.0, 0.0, 0.0, 0.0],
                provider="fake",
                model="fake-model",
                dimension=4,
            )

    monkeypatch.setattr(
        "app.services.search.OpenAIEmbeddingProvider",
        lambda **kwargs: _FakeQueryProvider(),
    )

    settings = _Settings()
    settings.model = "fake-model"
    settings.dimension = 4
    monkeypatch.setattr("app.services.search.load_embedding_settings", lambda: settings)

    query, results = await search_document(
        document_id,
        "  hello   world  ",
        5,
        session=object(),  # type: ignore[arg-type]
    )

    assert query == "hello world"
    assert call_count == 1
    assert results[0].chunk_id == chunk.id
    assert results[0].score == 0.9
    assert retrieval_repo.search_calls[0]["document_id"] == document_id
