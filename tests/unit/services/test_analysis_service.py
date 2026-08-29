"""Service-level analysis tests using fakes for the repository, provider,
and graph-runner boundaries, so no database or network is required.

Covers: fake-provider-backed graph success persists one result, repeated
POST reuses the existing result without invoking classification or the
graph again, unknown/textless documents never invoke a provider, and
provider/graph failures propagate as the expected typed errors.
"""

import uuid
from typing import Any

import pytest
from app.services.analysis import (
    AnalysisNotFoundError,
    DocumentNotFoundError,
    TextlessDocumentError,
    analyze,
    get_latest_analysis,
)

from agent.analysis.provider import ProviderUnavailableError
from agent.analysis.result import AnalysisFailedError, GenericAnalysisResult
from agent.analysis.types import DocumentSummaryCandidate


class _FakePage:
    def __init__(self, page_number: int, text: str) -> None:
        self.page_number = page_number
        self.text = text


class _FakeSection:
    def __init__(self, title: str) -> None:
        self.title = title


class _FakeDocument:
    def __init__(self, *, document_id: uuid.UUID, pages=None, sections=None) -> None:
        self.id = document_id
        self.filename = "doc.pdf"
        self.status = "parsed"
        self.pages = pages if pages is not None else [_FakePage(1, "Some real text.")]
        self.sections = sections or []


class _FakeDocumentRepository:
    def __init__(self, document: _FakeDocument | None) -> None:
        self._document = document

    def __call__(self, _session: Any) -> "_FakeDocumentRepository":
        return self

    async def get(self, document_id: uuid.UUID):
        return self._document


class _FakeClassification:
    def __init__(self, document_type: str = "generic", confidence: float = 0.9) -> None:
        self.document_type = document_type
        self.confidence = confidence


class _FakeAnalysis:
    def __init__(self, document_id: uuid.UUID) -> None:
        self.id = uuid.uuid4()
        self.document_id = document_id


class _FakeAnalysisRepository:
    def __init__(self, existing: _FakeAnalysis | None = None) -> None:
        self.existing = existing
        self.create_calls: list[dict[str, Any]] = []

    def __call__(self, _session: Any) -> "_FakeAnalysisRepository":
        return self

    async def get_latest_completed(self, document_id: uuid.UUID):
        return self.existing

    async def create(self, **kwargs: Any) -> _FakeAnalysis:
        self.create_calls.append(kwargs)
        return _FakeAnalysis(kwargs["document_id"])


def _result() -> GenericAnalysisResult:
    return GenericAnalysisResult(
        summary=DocumentSummaryCandidate(purpose="p", summary="s"),
        provider="fake",
        model="fake-model",
    )


@pytest.mark.asyncio
async def test_fake_graph_success_persists_one_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    document = _FakeDocument(document_id=document_id)
    document_repo = _FakeDocumentRepository(document)
    analysis_repo = _FakeAnalysisRepository(existing=None)

    monkeypatch.setattr("app.services.analysis.DocumentRepository", document_repo)
    monkeypatch.setattr("app.services.analysis.AnalysisRepository", analysis_repo)

    async def fake_ensure_classification(_document_id, _session, **_kwargs):
        return _FakeClassification()

    monkeypatch.setattr(
        "app.services.analysis.ensure_classification_result", fake_ensure_classification
    )
    monkeypatch.setattr(
        "app.services.analysis._build_provider", lambda settings: object()
    )

    async def fake_run_graph(initial_state):
        assert initial_state["document_type"] == "generic"
        return {"status": "completed", "result": _result()}

    monkeypatch.setattr("app.services.analysis.run_analysis_graph", fake_run_graph)

    analysis = await analyze(document_id, session=object())  # type: ignore[arg-type]

    assert analysis.document_id == document_id
    assert len(analysis_repo.create_calls) == 1


@pytest.mark.asyncio
async def test_repeated_post_uses_existing_result_without_classification_or_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    document = _FakeDocument(document_id=document_id)
    existing = _FakeAnalysis(document_id)
    document_repo = _FakeDocumentRepository(document)
    analysis_repo = _FakeAnalysisRepository(existing=existing)

    monkeypatch.setattr("app.services.analysis.DocumentRepository", document_repo)
    monkeypatch.setattr("app.services.analysis.AnalysisRepository", analysis_repo)

    async def _fail_classify(_document_id, _session, **_kwargs):
        raise AssertionError("must not ensure classification on repeated POST")

    monkeypatch.setattr(
        "app.services.analysis.ensure_classification_result", _fail_classify
    )

    async def _fail_graph(_state):
        raise AssertionError("must not invoke the graph on repeated POST")

    monkeypatch.setattr("app.services.analysis.run_analysis_graph", _fail_graph)

    analysis = await analyze(document_id, session=object())  # type: ignore[arg-type]

    assert analysis is existing
    assert analysis_repo.create_calls == []


@pytest.mark.asyncio
async def test_unknown_document_never_invokes_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_repo = _FakeDocumentRepository(None)
    monkeypatch.setattr("app.services.analysis.DocumentRepository", document_repo)

    async def _fail_classify(_document_id, _session, **_kwargs):
        raise AssertionError("must not ensure classification for an unknown document")

    monkeypatch.setattr(
        "app.services.analysis.ensure_classification_result", _fail_classify
    )

    with pytest.raises(DocumentNotFoundError):
        await analyze(uuid.uuid4(), session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_textless_document_fails_before_provider_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    document = _FakeDocument(document_id=document_id, pages=[_FakePage(1, "")])
    document_repo = _FakeDocumentRepository(document)
    analysis_repo = _FakeAnalysisRepository(existing=None)

    monkeypatch.setattr("app.services.analysis.DocumentRepository", document_repo)
    monkeypatch.setattr("app.services.analysis.AnalysisRepository", analysis_repo)

    async def _must_not_classify(_document_id, _session, **_kwargs):
        raise AssertionError("textless documents must fail before classification")

    monkeypatch.setattr(
        "app.services.analysis.ensure_classification_result", _must_not_classify
    )

    with pytest.raises(TextlessDocumentError):
        await analyze(document_id, session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_missing_provider_configuration_maps_to_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    document = _FakeDocument(document_id=document_id)
    document_repo = _FakeDocumentRepository(document)
    analysis_repo = _FakeAnalysisRepository(existing=None)

    monkeypatch.setattr("app.services.analysis.DocumentRepository", document_repo)
    monkeypatch.setattr("app.services.analysis.AnalysisRepository", analysis_repo)

    async def fake_ensure_classification(_document_id, _session, **_kwargs):
        return _FakeClassification()

    monkeypatch.setattr(
        "app.services.analysis.ensure_classification_result", fake_ensure_classification
    )

    def _raise_unavailable(settings):
        raise ProviderUnavailableError("not configured")

    monkeypatch.setattr("app.services.analysis._build_provider", _raise_unavailable)

    with pytest.raises(ProviderUnavailableError):
        await analyze(document_id, session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_failed_graph_run_raises_analysis_failed_without_persisting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    document = _FakeDocument(document_id=document_id)
    document_repo = _FakeDocumentRepository(document)
    analysis_repo = _FakeAnalysisRepository(existing=None)

    monkeypatch.setattr("app.services.analysis.DocumentRepository", document_repo)
    monkeypatch.setattr("app.services.analysis.AnalysisRepository", analysis_repo)

    async def fake_ensure_classification(_document_id, _session, **_kwargs):
        return _FakeClassification()

    monkeypatch.setattr(
        "app.services.analysis.ensure_classification_result", fake_ensure_classification
    )
    monkeypatch.setattr(
        "app.services.analysis._build_provider", lambda settings: object()
    )

    async def fake_run_graph(_state):
        return {"status": "failed", "failure_reason": "still invalid", "result": None}

    monkeypatch.setattr("app.services.analysis.run_analysis_graph", fake_run_graph)

    with pytest.raises(AnalysisFailedError):
        await analyze(document_id, session=object())  # type: ignore[arg-type]

    assert analysis_repo.create_calls == []


@pytest.mark.asyncio
async def test_get_latest_analysis_raises_not_found_for_unknown_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_repo = _FakeDocumentRepository(None)
    monkeypatch.setattr("app.services.analysis.DocumentRepository", document_repo)

    with pytest.raises(DocumentNotFoundError):
        await get_latest_analysis(uuid.uuid4(), session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_latest_analysis_raises_not_found_without_completed_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id = uuid.uuid4()
    document = _FakeDocument(document_id=document_id)
    document_repo = _FakeDocumentRepository(document)
    analysis_repo = _FakeAnalysisRepository(existing=None)

    monkeypatch.setattr("app.services.analysis.DocumentRepository", document_repo)
    monkeypatch.setattr("app.services.analysis.AnalysisRepository", analysis_repo)

    with pytest.raises(AnalysisNotFoundError):
        await get_latest_analysis(document_id, session=object())  # type: ignore[arg-type]
