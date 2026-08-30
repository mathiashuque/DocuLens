"""Route/state-transition tests for the compiled graph: valid, retryable-
invalid, exhausted-retry, and non-retryable failure paths. Proves only
invalid subsets are regenerated and valid items are preserved."""

import pytest

from agent.analysis.graph import run_analysis_graph
from agent.analysis.provider import (
    ProviderMetadata,
    ProviderRequestError,
    ProviderUnavailableError,
)
from agent.analysis.types import (
    DocumentSummaryCandidate,
    FindingCandidate,
    GenericAnalysisCandidate,
    RepairCandidate,
)

PAGE_TEXT = "The term renews automatically each year on notice."


def _summary() -> DocumentSummaryCandidate:
    return DocumentSummaryCandidate(purpose="p", summary="s")


def _base_state(provider: object, **overrides: object) -> dict:
    state = {
        "document_id": "doc-1",
        "filename": "doc.pdf",
        "pages": [(1, PAGE_TEXT)],
        "section_titles": [],
        "provider": provider,
        "document_type": "generic",
        "classification_confidence": 0.9,
    }
    state.update(overrides)
    return state


class _FakeProvider:
    def __init__(self, extract_outcomes, repair_outcomes=None):
        self._extract_outcomes = list(extract_outcomes)
        self._repair_outcomes = list(repair_outcomes or [])
        self.extract_calls = 0
        self.repair_calls = 0

    async def extract(self, *, system_instruction, user_content):
        self.extract_calls += 1
        outcome = self._extract_outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome, ProviderMetadata(provider="fake", model="m")

    async def repair(self, *, system_instruction, user_content):
        self.repair_calls += 1
        outcome = self._repair_outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome, ProviderMetadata(provider="fake", model="m")


def _finding(**overrides: object) -> FindingCandidate:
    base: dict[str, object] = {
        "title": "Auto-renewal",
        "description": "d",
        "category": "renewal",
        "importance": "high",
        "source_page": 1,
        "evidence": "renews automatically each year",
        "confidence": 0.9,
    }
    base.update(overrides)
    return FindingCandidate.model_validate(base)


@pytest.mark.asyncio
async def test_valid_candidate_persists_without_retry() -> None:
    candidate = GenericAnalysisCandidate(
        summary=_summary(), findings=[_finding()], important_dates=[], risks=[]
    )
    provider = _FakeProvider([candidate])
    state = _base_state(provider)

    result = await run_analysis_graph(state)

    assert result["status"] == "completed"
    assert len(result["result"].findings) == 1
    assert provider.extract_calls == 1
    assert provider.repair_calls == 0


@pytest.mark.asyncio
async def test_invalid_subset_triggers_one_retry_and_preserves_valid_items() -> None:
    good_finding = _finding(title="Good")
    bad_finding = _finding(title="Bad", evidence="not on the page anywhere")
    candidate = GenericAnalysisCandidate(
        summary=_summary(),
        findings=[good_finding, bad_finding],
        important_dates=[],
        risks=[],
    )
    fixed_finding = _finding(title="Fixed")
    repair = RepairCandidate(findings=[fixed_finding])
    provider = _FakeProvider([candidate], [repair])
    state = _base_state(provider)

    result = await run_analysis_graph(state)

    assert result["status"] == "completed"
    titles = {f.title for f in result["result"].findings}
    assert titles == {"Good", "Fixed"}
    assert provider.extract_calls == 1
    assert provider.repair_calls == 1


@pytest.mark.asyncio
async def test_still_invalid_after_retry_fails_safely() -> None:
    bad_finding = _finding(evidence="not on the page anywhere")
    candidate = GenericAnalysisCandidate(
        summary=_summary(), findings=[bad_finding], important_dates=[], risks=[]
    )
    still_bad_repair = RepairCandidate(
        findings=[_finding(evidence="still not present")]
    )
    provider = _FakeProvider([candidate], [still_bad_repair])
    state = _base_state(provider)

    result = await run_analysis_graph(state)

    assert result["status"] == "failed"
    assert result["result"] is None
    assert provider.extract_calls == 1
    assert provider.repair_calls == 1


@pytest.mark.asyncio
async def test_no_usable_text_fails_before_any_provider_call() -> None:
    provider = _FakeProvider([])
    state = _base_state(provider, pages=[(1, "   ")])

    result = await run_analysis_graph(state)

    assert result["status"] == "failed"
    assert provider.extract_calls == 0


@pytest.mark.asyncio
async def test_missing_classification_fails_before_any_provider_call() -> None:
    provider = _FakeProvider([])
    state = _base_state(provider)
    del state["document_type"]

    result = await run_analysis_graph(state)

    assert result["status"] == "failed"
    assert provider.extract_calls == 0


@pytest.mark.asyncio
async def test_retryable_transport_error_is_retried_once_at_extract() -> None:
    candidate = GenericAnalysisCandidate(summary=_summary(), findings=[_finding()])
    provider = _FakeProvider(
        [ProviderRequestError("timeout", retryable=True), candidate]
    )
    state = _base_state(provider)

    result = await run_analysis_graph(state)

    assert result["status"] == "completed"
    assert provider.extract_calls == 2


@pytest.mark.asyncio
async def test_non_retryable_provider_error_propagates_out_of_graph() -> None:
    provider = _FakeProvider([ProviderRequestError("auth failed", retryable=False)])
    state = _base_state(provider)

    with pytest.raises(ProviderRequestError):
        await run_analysis_graph(state)


@pytest.mark.asyncio
async def test_provider_unavailable_propagates_out_of_graph() -> None:
    provider = _FakeProvider([ProviderUnavailableError("not configured")])
    state = _base_state(provider)

    with pytest.raises(ProviderUnavailableError):
        await run_analysis_graph(state)
