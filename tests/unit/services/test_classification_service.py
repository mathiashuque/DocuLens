"""Service-level classification tests using fakes for the repository and
provider boundaries, so no database or network is required.

Covers: fake-provider success persists one result, repeated POST reuses the
existing result without another provider call, and ocr_required/unknown/
textless documents never invoke the provider.
"""

import uuid
from typing import Any

import pytest
from app.core.config import ClassificationSettings
from app.services.classification import (
    DocumentNotFoundError,
    TextlessDocumentError,
    classify,
    get_latest_classification,
)

from agent.classification.classifier import ClassifiedResult
from agent.classification.provider import ProviderUnavailableError


class _FakePage:
    def __init__(self, page_number: int, text: str) -> None:
        self.page_number = page_number
        self.text = text


class _FakeSection:
    def __init__(self, title: str) -> None:
        self.title = title


class _FakeDocument:
    def __init__(
        self,
        *,
        document_id: uuid.UUID,
        status: str = "parsed",
        pages: list[_FakePage] | None = None,
        sections: list[_FakeSection] | None = None,
    ) -> None:
        self.id = document_id
        self.filename = "doc.pdf"
        self.status = status
        self.pages = pages if pages is not None else [_FakePage(1, "Some real text.")]
        self.sections = sections or []


class _FakeDocumentRepository:
    def __init__(self, document: _FakeDocument | None) -> None:
        self._document = document

    def __call__(self, _session: Any) -> "_FakeDocumentRepository":
        return self

    async def get(self, document_id: uuid.UUID) -> _FakeDocument | None:
        return self._document


class _FakeClassification:
    def __init__(self, document_id: uuid.UUID) -> None:
        self.id = uuid.uuid4()
        self.document_id = document_id
        self.document_type = "contract"
        self.confidence = 0.9
        self.reason = "existing"
        self.evidence: list[dict[str, object]] = []
        self.provider = "openai"
        self.model = "gpt-4o-mini"
        self.status = "completed"


class _FakeClassificationRepository:
    def __init__(self, existing: _FakeClassification | None = None) -> None:
        self.existing = existing
        self.create_calls: list[dict[str, Any]] = []

    def __call__(self, _session: Any) -> "_FakeClassificationRepository":
        return self

    async def get_latest_completed(
        self, document_id: uuid.UUID
    ) -> _FakeClassification | None:
        return self.existing

    async def create(self, **kwargs: Any) -> _FakeClassification:
        self.create_calls.append(kwargs)
        result = _FakeClassification(kwargs["document_id"])
        result.document_type = kwargs["document_type"]
        return result


def _settings(**overrides: object) -> ClassificationSettings:
    base: dict[str, object] = {
        "api_key": "fake-key",
        "model": "gpt-4o-mini",
        "confidence_threshold": 0.65,
        "timeout_seconds": 30.0,
        "max_output_tokens": 800,
    }
    base.update(overrides)
    return ClassificationSettings(**base)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_fake_provider_success_persists_one_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    document = _FakeDocument(document_id=document_id)
    document_repo = _FakeDocumentRepository(document)
    classification_repo = _FakeClassificationRepository(existing=None)

    monkeypatch.setattr("app.services.classification.DocumentRepository", document_repo)
    monkeypatch.setattr(
        "app.services.classification.ClassificationRepository", classification_repo
    )
    monkeypatch.setattr(
        "app.services.classification.load_classification_settings", _settings
    )
    monkeypatch.setattr(
        "app.services.classification._build_provider", lambda settings: object()
    )

    async def fake_classify_document(**kwargs: Any) -> ClassifiedResult:
        from agent.classification.types import ClassificationEvidenceItem

        return ClassifiedResult(
            document_type="contract",
            confidence=0.9,
            reason="ok",
            evidence=(ClassificationEvidenceItem(page=1, text="Some real text"),),
            provider="fake",
            model="fake-model",
            latency_ms=10,
            input_tokens=5,
            output_tokens=5,
        )

    monkeypatch.setattr(
        "app.services.classification.classify_document", fake_classify_document
    )

    result = await classify(document_id, session=object())  # type: ignore[arg-type]

    assert result.document_type == "contract"
    assert len(classification_repo.create_calls) == 1


@pytest.mark.asyncio
async def test_repeated_post_uses_existing_result_without_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    document = _FakeDocument(document_id=document_id)
    existing = _FakeClassification(document_id)
    document_repo = _FakeDocumentRepository(document)
    classification_repo = _FakeClassificationRepository(existing=existing)

    monkeypatch.setattr("app.services.classification.DocumentRepository", document_repo)
    monkeypatch.setattr(
        "app.services.classification.ClassificationRepository", classification_repo
    )

    def _fail_build_provider(settings: object) -> object:
        raise AssertionError("must not construct a provider on repeated POST")

    monkeypatch.setattr(
        "app.services.classification._build_provider", _fail_build_provider
    )

    result = await classify(document_id, session=object())  # type: ignore[arg-type]

    assert result is existing
    assert classification_repo.create_calls == []


@pytest.mark.asyncio
async def test_unknown_document_never_invokes_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_repo = _FakeDocumentRepository(None)
    monkeypatch.setattr("app.services.classification.DocumentRepository", document_repo)

    def _fail_build_provider(settings: object) -> object:
        raise AssertionError("must not construct a provider for an unknown document")

    monkeypatch.setattr(
        "app.services.classification._build_provider", _fail_build_provider
    )

    with pytest.raises(DocumentNotFoundError):
        await classify(uuid.uuid4(), session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_ocr_required_document_never_invokes_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    document = _FakeDocument(
        document_id=document_id, status="ocr_required", pages=[_FakePage(1, "")]
    )
    document_repo = _FakeDocumentRepository(document)
    monkeypatch.setattr("app.services.classification.DocumentRepository", document_repo)

    def _fail_build_provider(settings: object) -> object:
        raise AssertionError("must not construct a provider for ocr_required")

    monkeypatch.setattr(
        "app.services.classification._build_provider", _fail_build_provider
    )

    with pytest.raises(TextlessDocumentError):
        await classify(document_id, session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_textless_parsed_document_never_invokes_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    document = _FakeDocument(
        document_id=document_id,
        status="parsed",
        pages=[_FakePage(1, "   "), _FakePage(2, "")],
    )
    document_repo = _FakeDocumentRepository(document)
    monkeypatch.setattr("app.services.classification.DocumentRepository", document_repo)

    def _fail_build_provider(settings: object) -> object:
        raise AssertionError("must not construct a provider for textless documents")

    monkeypatch.setattr(
        "app.services.classification._build_provider", _fail_build_provider
    )

    with pytest.raises(TextlessDocumentError):
        await classify(document_id, session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_missing_provider_configuration_maps_to_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    document = _FakeDocument(document_id=document_id)
    document_repo = _FakeDocumentRepository(document)
    classification_repo = _FakeClassificationRepository(existing=None)

    monkeypatch.setattr("app.services.classification.DocumentRepository", document_repo)
    monkeypatch.setattr(
        "app.services.classification.ClassificationRepository", classification_repo
    )
    monkeypatch.setattr(
        "app.services.classification.load_classification_settings",
        lambda: _settings(api_key=None),
    )

    with pytest.raises(ProviderUnavailableError):
        await classify(document_id, session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_latest_classification_raises_not_found_for_unknown_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_repo = _FakeDocumentRepository(None)
    monkeypatch.setattr("app.services.classification.DocumentRepository", document_repo)

    with pytest.raises(DocumentNotFoundError):
        await get_latest_classification(uuid.uuid4(), session=object())  # type: ignore[arg-type]
