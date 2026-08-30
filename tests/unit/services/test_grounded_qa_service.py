"""Service-level grounded-QA tests using fakes for retrieval and the
generation provider boundary; no database or network required.

Covers: one retrieval call per request, question/top_k validation delegated
to retrieval's own bounds, empty usable retrieval skipping generation,
valid single/multi citation answers, bounded repair success/exhaustion, and
safe error mapping for a missing/failing provider.
"""

import uuid
from typing import Any

import pytest
from app.services.grounded_qa import (
    AnsweredResult,
    InsufficientEvidenceResult,
    InvalidQuestionError,
    answer_question,
)
from app.services.search import SearchResultItem

from agent.grounded_qa.provider import ProviderRequestError, ProviderUnavailableError
from agent.grounded_qa.types import CitationCandidate, GroundedAnswerCandidate


def _result(
    chunk_id: uuid.UUID, text: str, page_start: int = 1, page_end: int | None = None
) -> SearchResultItem:
    return SearchResultItem(
        chunk_id=chunk_id,
        chunk_index=0,
        text=text,
        page_start=page_start,
        page_end=page_end if page_end is not None else page_start,
        section_id=None,
        section_title=None,
        section_path=[],
        score=0.9,
    )


class _FakePage:
    def __init__(self, page_number: int, text: str) -> None:
        self.page_number = page_number
        self.text = text


class _FakeDocument:
    def __init__(self, pages: dict[int, str]) -> None:
        self.pages = [_FakePage(n, t) for n, t in pages.items()]


class _FakeDocumentRepository:
    def __init__(self, document: _FakeDocument) -> None:
        self._document = document

    def __call__(self, _session: Any) -> "_FakeDocumentRepository":
        return self

    async def get(self, _document_id: uuid.UUID):
        return self._document


class _FakeProvider:
    def __init__(
        self,
        answer_candidate: GroundedAnswerCandidate,
        repair_candidate: GroundedAnswerCandidate | None = None,
        *,
        fail_repair: bool = False,
    ) -> None:
        self.answer_candidate = answer_candidate
        self.repair_candidate = repair_candidate
        self.fail_repair = fail_repair
        self.answer_calls = 0
        self.repair_calls = 0

    async def answer(self, *, system_instruction: str, user_content: str):
        self.answer_calls += 1
        from agent.grounded_qa.provider import ProviderMetadata

        return self.answer_candidate, ProviderMetadata(provider="fake", model="fake")

    async def repair(self, *, system_instruction: str, user_content: str):
        self.repair_calls += 1
        if self.fail_repair:
            raise ProviderRequestError("repair failed", retryable=False)
        from agent.grounded_qa.provider import ProviderMetadata

        assert self.repair_candidate is not None
        return self.repair_candidate, ProviderMetadata(provider="fake", model="fake")


def _patch_search(
    monkeypatch: pytest.MonkeyPatch,
    results: list[SearchResultItem],
    document: _FakeDocument,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    async def _fake_search_document(document_id, raw_query, top_k, session):
        calls.append({"document_id": document_id, "query": raw_query, "top_k": top_k})
        return raw_query, results

    monkeypatch.setattr(
        "app.services.grounded_qa.search_document", _fake_search_document
    )
    monkeypatch.setattr(
        "app.services.grounded_qa.DocumentRepository", _FakeDocumentRepository(document)
    )
    return calls


@pytest.mark.asyncio
async def test_blank_question_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_search(monkeypatch, [], _FakeDocument({}))
    with pytest.raises(InvalidQuestionError):
        await answer_question(uuid.uuid4(), "   ", 5, session=object())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_empty_retrieval_skips_generation_and_returns_insufficient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_search(monkeypatch, [], _FakeDocument({}))
    provider_calls = {"n": 0}

    class _NeverCalledProvider:
        async def answer(self, **kwargs):
            provider_calls["n"] += 1
            raise AssertionError("must not call provider without usable context")

        async def repair(self, **kwargs):
            provider_calls["n"] += 1
            raise AssertionError("must not call provider without usable context")

    result = await answer_question(
        uuid.uuid4(),
        "Who approved this?",
        5,
        session=object(),
        provider=_NeverCalledProvider(),  # type: ignore[arg-type]
    )
    assert isinstance(result, InsufficientEvidenceResult)
    assert result.citations == ()
    assert provider_calls["n"] == 0
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_one_retrieval_call_per_request(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk_id = uuid.uuid4()
    document_id = uuid.uuid4()
    page_text = (
        "The agreement renews automatically for successive twelve month periods."
    )
    calls = _patch_search(
        monkeypatch, [_result(chunk_id, page_text)], _FakeDocument({1: page_text})
    )
    candidate = GroundedAnswerCandidate(
        status="answered",
        answer="Yes, it renews automatically.",
        citations=[
            CitationCandidate(
                chunk_id=str(chunk_id), page=1, evidence="renews automatically"
            )
        ],
    )
    result = await answer_question(
        document_id,
        "Does it renew?",
        5,
        session=object(),
        provider=_FakeProvider(candidate),  # type: ignore[arg-type]
    )
    assert isinstance(result, AnsweredResult)
    assert len(calls) == 1
    assert calls[0]["document_id"] == document_id


@pytest.mark.asyncio
async def test_valid_multi_citation_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk_a, chunk_b = uuid.uuid4(), uuid.uuid4()
    page_1 = "The agreement renews automatically for successive twelve month periods."
    page_2 = "Either party may terminate this agreement with sixty days written notice."
    _patch_search(
        monkeypatch,
        [_result(chunk_a, page_1, 1), _result(chunk_b, page_2, 2)],
        _FakeDocument({1: page_1, 2: page_2}),
    )
    candidate = GroundedAnswerCandidate(
        status="answered",
        answer="It renews automatically and either party may terminate with notice.",
        citations=[
            CitationCandidate(
                chunk_id=str(chunk_a), page=1, evidence="renews automatically"
            ),
            CitationCandidate(
                chunk_id=str(chunk_b),
                page=2,
                evidence="terminate this agreement with sixty days written notice",
            ),
        ],
    )
    result = await answer_question(
        uuid.uuid4(),
        "Does it renew and can it be terminated?",
        5,
        session=object(),
        provider=_FakeProvider(candidate),  # type: ignore[arg-type]
    )
    assert isinstance(result, AnsweredResult)
    assert len(result.citations) == 2


@pytest.mark.asyncio
async def test_repair_succeeds_once_after_invalid_first_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk_id = uuid.uuid4()
    page_text = (
        "The agreement renews automatically for successive twelve month periods."
    )
    _patch_search(
        monkeypatch, [_result(chunk_id, page_text)], _FakeDocument({1: page_text})
    )
    invalid_first = GroundedAnswerCandidate(
        status="answered",
        answer="It renews.",
        citations=[
            CitationCandidate(
                chunk_id=str(chunk_id), page=1, evidence="text never in the chunk"
            )
        ],
    )
    valid_repair = GroundedAnswerCandidate(
        status="answered",
        answer="It renews automatically.",
        citations=[
            CitationCandidate(
                chunk_id=str(chunk_id), page=1, evidence="renews automatically"
            )
        ],
    )
    provider = _FakeProvider(invalid_first, valid_repair)
    result = await answer_question(
        uuid.uuid4(),
        "Does it renew?",
        5,
        session=object(),
        provider=provider,  # type: ignore[arg-type]
    )
    assert isinstance(result, AnsweredResult)
    assert provider.answer_calls == 1
    assert provider.repair_calls == 1


@pytest.mark.asyncio
async def test_repair_exhausts_once_and_returns_insufficient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk_id = uuid.uuid4()
    page_text = (
        "The agreement renews automatically for successive twelve month periods."
    )
    _patch_search(
        monkeypatch, [_result(chunk_id, page_text)], _FakeDocument({1: page_text})
    )
    invalid_first = GroundedAnswerCandidate(
        status="answered",
        answer="It renews.",
        citations=[
            CitationCandidate(
                chunk_id=str(chunk_id), page=1, evidence="text never in the chunk"
            )
        ],
    )
    still_invalid_repair = GroundedAnswerCandidate(
        status="answered",
        answer="It renews.",
        citations=[
            CitationCandidate(
                chunk_id=str(chunk_id), page=1, evidence="still never in the chunk"
            )
        ],
    )
    provider = _FakeProvider(invalid_first, still_invalid_repair)
    result = await answer_question(
        uuid.uuid4(),
        "Does it renew?",
        5,
        session=object(),
        provider=provider,  # type: ignore[arg-type]
    )
    assert isinstance(result, InsufficientEvidenceResult)
    assert provider.answer_calls == 1
    assert provider.repair_calls == 1  # never loops beyond one repair attempt


@pytest.mark.asyncio
async def test_no_repair_when_first_candidate_is_insufficient_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk_id = uuid.uuid4()
    page_text = "Some unrelated page text."
    _patch_search(
        monkeypatch, [_result(chunk_id, page_text)], _FakeDocument({1: page_text})
    )
    candidate = GroundedAnswerCandidate(
        status="insufficient_evidence", answer="not enough evidence", citations=[]
    )
    provider = _FakeProvider(candidate)
    result = await answer_question(
        uuid.uuid4(),
        "Who approved the budget?",
        5,
        session=object(),
        provider=provider,  # type: ignore[arg-type]
    )
    assert isinstance(result, InsufficientEvidenceResult)
    assert provider.repair_calls == 0


@pytest.mark.asyncio
async def test_provider_failure_during_repair_propagates_as_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk_id = uuid.uuid4()
    page_text = (
        "The agreement renews automatically for successive twelve month periods."
    )
    _patch_search(
        monkeypatch, [_result(chunk_id, page_text)], _FakeDocument({1: page_text})
    )
    invalid_first = GroundedAnswerCandidate(
        status="answered",
        answer="It renews.",
        citations=[
            CitationCandidate(
                chunk_id=str(chunk_id), page=1, evidence="never in the chunk"
            )
        ],
    )
    provider = _FakeProvider(invalid_first, fail_repair=True)
    with pytest.raises(ProviderRequestError):
        await answer_question(
            uuid.uuid4(),
            "Does it renew?",
            5,
            session=object(),
            provider=provider,  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_missing_provider_configuration_maps_to_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk_id = uuid.uuid4()
    page_text = "Some page text with enough content."
    _patch_search(
        monkeypatch, [_result(chunk_id, page_text)], _FakeDocument({1: page_text})
    )

    class _Settings:
        api_key = None
        model = "gpt-4o-mini"
        timeout_seconds = 1.0
        max_output_tokens = 100
        max_context_chunks = 5
        max_context_chars = 8000
        max_question_chars = 2000

    monkeypatch.setattr(
        "app.services.grounded_qa.load_grounded_qa_settings", lambda: _Settings()
    )
    with pytest.raises(ProviderUnavailableError):
        await answer_question(uuid.uuid4(), "Does it renew?", 5, session=object())  # type: ignore[arg-type]
