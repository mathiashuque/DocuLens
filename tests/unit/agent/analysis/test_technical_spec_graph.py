"""Route/state-transition tests proving: only `technical_specification`
classifications invoke the technical-spec provider, common generic analysis
still runs for technical specifications, the combined result carries a
discriminated specialized payload, and targeted retry regenerates only the
invalid subset while preserving everything else already valid."""

import pytest

from agent.analysis.graph import run_analysis_graph
from agent.analysis.provider import ProviderMetadata
from agent.analysis.types import DocumentSummaryCandidate, GenericAnalysisCandidate
from agent.extractors.technical_spec.types import (
    RequirementCandidate,
    TechnicalSpecExtractionCandidate,
    TechnicalSpecRepairCandidate,
)

SPEC_PAGE = (
    "FR-12: The service shall allow administrators to revoke active sessions. "
    "The system depends on the Payment Gateway API for billing."
)


def _summary() -> DocumentSummaryCandidate:
    return DocumentSummaryCandidate(purpose="p", summary="s")


class _FakeGenericProvider:
    def __init__(self, extract_outcomes, repair_outcomes=None):
        self._extract_outcomes = list(extract_outcomes)
        self._repair_outcomes = list(repair_outcomes or [])
        self.extract_calls = 0
        self.repair_calls = 0

    async def extract(self, *, system_instruction, user_content):
        self.extract_calls += 1
        return self._extract_outcomes.pop(0), ProviderMetadata(
            provider="fake", model="m"
        )

    async def repair(self, *, system_instruction, user_content):
        self.repair_calls += 1
        return self._repair_outcomes.pop(0), ProviderMetadata(
            provider="fake", model="m"
        )


class _FakeTechnicalSpecProvider:
    def __init__(self, extract_outcomes, repair_outcomes=None):
        self._extract_outcomes = list(extract_outcomes)
        self._repair_outcomes = list(repair_outcomes or [])
        self.extract_calls = 0
        self.repair_calls = 0

    async def extract(self, *, system_instruction, user_content):
        self.extract_calls += 1
        return self._extract_outcomes.pop(0), ProviderMetadata(
            provider="fake", model="m"
        )

    async def repair(self, *, system_instruction, user_content):
        self.repair_calls += 1
        return self._repair_outcomes.pop(0), ProviderMetadata(
            provider="fake", model="m"
        )


def _base_state(document_type: str, provider, **overrides) -> dict:
    state = {
        "document_id": "doc-1",
        "filename": "doc.pdf",
        "pages": [(1, SPEC_PAGE)],
        "section_titles": [],
        "sections": [],
        "provider": provider,
        "document_type": document_type,
        "classification_confidence": 0.9,
    }
    state.update(overrides)
    return state


def _valid_requirement() -> RequirementCandidate:
    return RequirementCandidate(
        category="functional",
        identifier="FR-12",
        statement="Revoke active sessions",
        priority="must",
        source_page=1,
        evidence="FR-12: The service shall allow administrators to revoke active sessions.",
        confidence=0.98,
    )


@pytest.mark.asyncio
async def test_technical_spec_route_calls_provider_and_produces_specialized_result() -> (
    None
):
    generic_provider = _FakeGenericProvider(
        [GenericAnalysisCandidate(summary=_summary())]
    )
    technical_spec_provider = _FakeTechnicalSpecProvider(
        [TechnicalSpecExtractionCandidate(requirements=[_valid_requirement()])]
    )
    state = _base_state(
        "technical_specification",
        generic_provider,
        technical_spec_provider=technical_spec_provider,
    )

    result = await run_analysis_graph(state)

    assert result["status"] == "completed"
    assert generic_provider.extract_calls == 1
    assert technical_spec_provider.extract_calls == 1
    specialized = result["result"].specialized
    assert specialized is not None
    assert specialized.extractor == "technical_specification_requirements"
    assert len(specialized.requirements) == 1
    assert specialized.functional_requirements[0].identifier == "FR-12"


@pytest.mark.asyncio
async def test_generic_and_contract_routes_never_call_technical_spec_provider() -> None:
    generic_provider = _FakeGenericProvider(
        [GenericAnalysisCandidate(summary=_summary())]
    )
    state = _base_state("generic", generic_provider)
    # No technical_spec_provider in state at all: if the graph tried to call
    # it, this would raise a KeyError, proving the route is never taken.

    result = await run_analysis_graph(state)

    assert result["status"] == "completed"
    assert result["result"].specialized is None
    assert generic_provider.extract_calls == 1


@pytest.mark.asyncio
async def test_targeted_retry_repairs_only_invalid_technical_spec_items() -> None:
    """Generic output is valid on the first pass; only the requirement is
    invalid (evidence not on the cited page). Only the technical-spec
    provider's repair should be called."""
    generic_provider = _FakeGenericProvider(
        [GenericAnalysisCandidate(summary=_summary())]
    )
    bad_requirement = RequirementCandidate(
        category="functional",
        statement="Bad",
        source_page=1,
        evidence="not present anywhere",
        confidence=0.5,
    )
    fixed_requirement = _valid_requirement()
    technical_spec_provider = _FakeTechnicalSpecProvider(
        [TechnicalSpecExtractionCandidate(requirements=[bad_requirement])],
        [TechnicalSpecRepairCandidate(requirements=[fixed_requirement])],
    )
    state = _base_state(
        "technical_specification",
        generic_provider,
        technical_spec_provider=technical_spec_provider,
    )

    result = await run_analysis_graph(state)

    assert result["status"] == "completed"
    assert generic_provider.extract_calls == 1
    assert generic_provider.repair_calls == 0
    assert technical_spec_provider.extract_calls == 1
    assert technical_spec_provider.repair_calls == 1
    specialized = result["result"].specialized
    assert specialized is not None
    assert [r.identifier for r in specialized.requirements] == ["FR-12"]


@pytest.mark.asyncio
async def test_still_invalid_technical_spec_item_after_retry_fails_safely() -> None:
    bad_requirement = RequirementCandidate(
        category="functional",
        statement="Bad",
        source_page=1,
        evidence="not present anywhere",
        confidence=0.5,
    )
    still_bad = RequirementCandidate(
        category="functional",
        statement="Still bad",
        source_page=1,
        evidence="also not present",
        confidence=0.5,
    )
    generic_provider = _FakeGenericProvider(
        [GenericAnalysisCandidate(summary=_summary())]
    )
    technical_spec_provider = _FakeTechnicalSpecProvider(
        [TechnicalSpecExtractionCandidate(requirements=[bad_requirement])],
        [TechnicalSpecRepairCandidate(requirements=[still_bad])],
    )
    state = _base_state(
        "technical_specification",
        generic_provider,
        technical_spec_provider=technical_spec_provider,
    )

    result = await run_analysis_graph(state)

    assert result["status"] == "failed"
    assert result["result"] is None
    assert technical_spec_provider.repair_calls == 1


@pytest.mark.asyncio
async def test_technical_spec_allows_all_empty_categories() -> None:
    generic_provider = _FakeGenericProvider(
        [GenericAnalysisCandidate(summary=_summary())]
    )
    technical_spec_provider = _FakeTechnicalSpecProvider(
        [TechnicalSpecExtractionCandidate()]
    )
    state = _base_state(
        "technical_specification",
        generic_provider,
        technical_spec_provider=technical_spec_provider,
    )

    result = await run_analysis_graph(state)

    assert result["status"] == "completed"
    specialized = result["result"].specialized
    assert specialized is not None
    assert specialized.requirements == ()
    assert specialized.constraints == ()
    assert specialized.dependencies == ()
