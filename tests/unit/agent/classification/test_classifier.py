"""Classifier orchestration: threshold routing, retry behavior, and
adversarial input handling, all against a fake provider (no network)."""

from collections.abc import Sequence

import pytest

from agent.classification.classifier import ClassificationFailedError, classify_document
from agent.classification.provider import ProviderMetadata, ProviderRequestError
from agent.classification.types import ClassificationCandidate

PAGES = [(1, "This Agreement is entered into by the parties on the terms below.")]


class _FakeProvider:
    def __init__(self, outcomes: Sequence[ClassificationCandidate | Exception]) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[str] = []

    async def classify(
        self, *, system_instruction: str, user_content: str
    ) -> tuple[ClassificationCandidate, ProviderMetadata]:
        self.calls.append(user_content)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome, ProviderMetadata(provider="fake", model="fake-model")


def _candidate(**overrides: object) -> ClassificationCandidate:
    base: dict[str, object] = {
        "document_type": "contract",
        "confidence": 0.9,
        "reason": "Defines parties and obligations.",
        "evidence": [
            {"page": 1, "text": "This Agreement is entered into by the parties"}
        ],
    }
    base.update(overrides)
    return ClassificationCandidate.model_validate(base)


@pytest.mark.asyncio
async def test_valid_high_confidence_result_is_returned_as_is() -> None:
    provider = _FakeProvider([_candidate(confidence=0.9)])

    result = await classify_document(
        filename="agreement.pdf",
        pages=PAGES,
        section_titles=[],
        provider=provider,
        confidence_threshold=0.65,
    )

    assert result.document_type == "contract"
    assert result.confidence == 0.9
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_low_confidence_specialized_candidate_routes_to_generic() -> None:
    provider = _FakeProvider([_candidate(document_type="contract", confidence=0.3)])

    result = await classify_document(
        filename="agreement.pdf",
        pages=PAGES,
        section_titles=[],
        provider=provider,
        confidence_threshold=0.65,
    )

    assert result.document_type == "generic"
    assert result.confidence == 0.3
    assert "uncertain" in result.reason.lower()


@pytest.mark.asyncio
async def test_low_confidence_generic_candidate_stays_generic_without_retry() -> None:
    provider = _FakeProvider([_candidate(document_type="generic", confidence=0.2)])

    result = await classify_document(
        filename="agreement.pdf",
        pages=PAGES,
        section_titles=[],
        provider=provider,
        confidence_threshold=0.65,
    )

    assert result.document_type == "generic"
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_invalid_evidence_then_valid_retry_succeeds_with_two_calls() -> None:
    bad = _candidate(evidence=[{"page": 1, "text": "text that is not on the page"}])
    good = _candidate()
    provider = _FakeProvider([bad, good])

    result = await classify_document(
        filename="agreement.pdf",
        pages=PAGES,
        section_titles=[],
        provider=provider,
        confidence_threshold=0.65,
    )

    assert result.document_type == "contract"
    assert len(provider.calls) == 2
    assert "correction_feedback" in provider.calls[1]


@pytest.mark.asyncio
async def test_exhausted_invalid_evidence_raises_without_persisting() -> None:
    bad = _candidate(evidence=[{"page": 1, "text": "text that is not on the page"}])
    provider = _FakeProvider([bad, bad])

    with pytest.raises(ClassificationFailedError):
        await classify_document(
            filename="agreement.pdf",
            pages=PAGES,
            section_titles=[],
            provider=provider,
            confidence_threshold=0.65,
        )

    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_retryable_provider_error_is_retried_once() -> None:
    provider = _FakeProvider(
        [ProviderRequestError("timed out", retryable=True), _candidate()]
    )

    result = await classify_document(
        filename="agreement.pdf",
        pages=PAGES,
        section_titles=[],
        provider=provider,
        confidence_threshold=0.65,
    )

    assert result.document_type == "contract"
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_non_retryable_provider_error_is_not_retried() -> None:
    provider = _FakeProvider([ProviderRequestError("auth failed", retryable=False)])

    with pytest.raises(ProviderRequestError):
        await classify_document(
            filename="agreement.pdf",
            pages=PAGES,
            section_titles=[],
            provider=provider,
            confidence_threshold=0.65,
        )

    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_retryable_error_exhausted_after_one_retry() -> None:
    provider = _FakeProvider(
        [
            ProviderRequestError("timed out", retryable=True),
            ProviderRequestError("timed out", retryable=True),
        ]
    )

    with pytest.raises(ProviderRequestError):
        await classify_document(
            filename="agreement.pdf",
            pages=PAGES,
            section_titles=[],
            provider=provider,
            confidence_threshold=0.65,
        )

    assert len(provider.calls) == 2
