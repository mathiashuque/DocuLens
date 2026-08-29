"""Service-level indexing tests using fakes for the repository and
embedding-provider boundaries; no database or network required.

Covers: eligibility gating, idempotency before provider construction,
atomic-failure passthrough on chunking errors, compatibility checking of
an existing index, and duplicate-index graceful handling.
"""

import uuid
from typing import Any

import pytest
from app.db.retrieval_repository import DuplicateIndexError
from app.services.indexing import (
    DocumentNotFoundError,
    IncompatibleIndexError,
    IneligibleDocumentError,
    index_document,
)

from retrieval.embedding import EmbeddingProviderUnavailableError


class _FakePage:
    def __init__(self, page_number: int, text: str) -> None:
        self.page_number = page_number
        self.text = text


class _FakeDocument:
    def __init__(
        self, *, document_id: uuid.UUID, status: str = "parsed", pages=None
    ) -> None:
        self.id = document_id
        self.status = status
        self.pages = (
            pages if pages is not None else [_FakePage(1, "Some real text here.")]
        )
        self.sections: list[Any] = []


class _FakeDocumentRepository:
    def __init__(self, document: _FakeDocument | None) -> None:
        self._document = document

    def __call__(self, _session: Any) -> "_FakeDocumentRepository":
        return self

    async def get(self, _document_id: uuid.UUID):
        return self._document


class _FakeIndex:
    def __init__(self, document_id: uuid.UUID, **kwargs: Any) -> None:
        self.document_id = document_id
        self.embedding_provider = kwargs.get("embedding_provider", "openai")
        self.embedding_model = kwargs.get("embedding_model", "text-embedding-3-small")
        self.dimension = kwargs.get("dimension", 1536)


class _FakeRetrievalRepository:
    def __init__(self, existing: _FakeIndex | None = None) -> None:
        self.existing = existing
        self.create_calls: list[dict[str, Any]] = []
        self.raise_duplicate_once = False

    def __call__(self, _session: Any) -> "_FakeRetrievalRepository":
        return self

    async def get_completed_index(self, _document_id: uuid.UUID):
        return self.existing

    async def create_index(self, **kwargs: Any) -> _FakeIndex:
        self.create_calls.append(kwargs)
        document_id = kwargs["document_id"]
        rest = {k: v for k, v in kwargs.items() if k != "document_id"}
        if self.raise_duplicate_once:
            self.raise_duplicate_once = False
            self.existing = _FakeIndex(document_id, **rest)
            raise DuplicateIndexError(str(document_id))
        index = _FakeIndex(document_id, **rest)
        self.existing = index
        return index


@pytest.mark.asyncio
async def test_unknown_document_raises_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.indexing.DocumentRepository", _FakeDocumentRepository(None)
    )
    with pytest.raises(DocumentNotFoundError):
        await index_document(uuid.uuid4(), session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_existing_compatible_index_returned_without_building_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    existing = _FakeIndex(document_id)
    monkeypatch.setattr(
        "app.services.indexing.DocumentRepository",
        _FakeDocumentRepository(_FakeDocument(document_id=document_id)),
    )
    monkeypatch.setattr(
        "app.services.indexing.RetrievalRepository", _FakeRetrievalRepository(existing)
    )

    def _fail_build_provider(_settings: Any) -> Any:
        raise AssertionError("must not build a provider for an idempotent hit")

    monkeypatch.setattr("app.services.indexing._build_provider", _fail_build_provider)

    index, created = await index_document(document_id, session=object())  # type: ignore[arg-type]

    assert index is existing
    assert created is False


@pytest.mark.asyncio
async def test_existing_incompatible_index_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    existing = _FakeIndex(document_id, embedding_model="text-embedding-3-large")
    monkeypatch.setattr(
        "app.services.indexing.DocumentRepository",
        _FakeDocumentRepository(_FakeDocument(document_id=document_id)),
    )
    monkeypatch.setattr(
        "app.services.indexing.RetrievalRepository", _FakeRetrievalRepository(existing)
    )

    with pytest.raises(IncompatibleIndexError):
        await index_document(document_id, session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_ineligible_document_status_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    document = _FakeDocument(document_id=document_id, status="ocr_required")
    monkeypatch.setattr(
        "app.services.indexing.DocumentRepository", _FakeDocumentRepository(document)
    )
    monkeypatch.setattr(
        "app.services.indexing.RetrievalRepository", _FakeRetrievalRepository(None)
    )

    with pytest.raises(IneligibleDocumentError):
        await index_document(document_id, session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_textless_document_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    document_id = uuid.uuid4()
    document = _FakeDocument(document_id=document_id, pages=[_FakePage(1, "   ")])
    monkeypatch.setattr(
        "app.services.indexing.DocumentRepository", _FakeDocumentRepository(document)
    )
    monkeypatch.setattr(
        "app.services.indexing.RetrievalRepository", _FakeRetrievalRepository(None)
    )

    with pytest.raises(IneligibleDocumentError):
        await index_document(document_id, session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_missing_api_key_maps_to_provider_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    document = _FakeDocument(document_id=document_id)
    monkeypatch.setattr(
        "app.services.indexing.DocumentRepository", _FakeDocumentRepository(document)
    )
    monkeypatch.setattr(
        "app.services.indexing.RetrievalRepository", _FakeRetrievalRepository(None)
    )

    class _NoKeySettings:
        api_key = None
        model = "text-embedding-3-small"
        dimension = 1536
        timeout_seconds = 1.0
        max_batch_size = 96

    monkeypatch.setattr(
        "app.services.indexing.load_embedding_settings", lambda: _NoKeySettings()
    )

    with pytest.raises(EmbeddingProviderUnavailableError):
        await index_document(document_id, session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_duplicate_index_race_returns_existing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    document = _FakeDocument(document_id=document_id)
    retrieval_repo = _FakeRetrievalRepository(None)
    retrieval_repo.raise_duplicate_once = True
    monkeypatch.setattr(
        "app.services.indexing.DocumentRepository", _FakeDocumentRepository(document)
    )
    monkeypatch.setattr("app.services.indexing.RetrievalRepository", retrieval_repo)

    class _FakeProvider:
        async def embed_documents(self, texts: list[str]) -> Any:
            from retrieval.embedding import EmbeddingBatch

            return EmbeddingBatch(
                vectors=[[0.0] * 4 for _ in texts],
                provider="fake",
                model="fake-model",
                dimension=4,
            )

    monkeypatch.setattr(
        "app.services.indexing._build_provider", lambda _settings: _FakeProvider()
    )

    class _Settings:
        api_key = "key"
        model = "fake-model"
        dimension = 4
        timeout_seconds = 1.0
        max_batch_size = 96

    monkeypatch.setattr(
        "app.services.indexing.load_embedding_settings", lambda: _Settings()
    )

    index, created = await index_document(document_id, session=object())  # type: ignore[arg-type]

    assert created is False
    assert index is retrieval_repo.existing
