"""Route/state-transition tests proving: only `contract` classifications
invoke the contract provider, common generic analysis still runs for
contracts, the combined result carries a discriminated specialized payload,
and targeted retry regenerates only the invalid subset (generic or
contract) while preserving everything else already valid."""

import pytest

from agent.analysis.graph import run_analysis_graph
from agent.analysis.provider import ProviderMetadata
from agent.analysis.types import DocumentSummaryCandidate, GenericAnalysisCandidate
from agent.extractors.contract.types import (
    ContractExtractionCandidate,
    ContractRepairCandidate,
    PartyCandidate,
)

CONTRACT_PAGE = (
    "This Services Agreement is between Northstar Hosting Ltd. (Provider) and "
    "Customer Inc. Provider shall maintain 99.9% monthly availability."
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


class _FakeContractProvider:
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
        "pages": [(1, CONTRACT_PAGE)],
        "section_titles": [],
        "sections": [],
        "provider": provider,
        "document_type": document_type,
        "classification_confidence": 0.9,
    }
    state.update(overrides)
    return state


def _valid_party() -> PartyCandidate:
    return PartyCandidate(
        name="Northstar Hosting Ltd.",
        role="provider",
        source_page=1,
        evidence="Northstar Hosting Ltd. (Provider)",
        confidence=0.9,
    )


@pytest.mark.asyncio
async def test_contract_route_calls_contract_provider_and_produces_specialized_result() -> (
    None
):
    generic_provider = _FakeGenericProvider(
        [GenericAnalysisCandidate(summary=_summary())]
    )
    contract_provider = _FakeContractProvider(
        [ContractExtractionCandidate(parties=[_valid_party()])]
    )
    state = _base_state(
        "contract", generic_provider, contract_provider=contract_provider
    )

    result = await run_analysis_graph(state)

    assert result["status"] == "completed"
    assert generic_provider.extract_calls == 1
    assert contract_provider.extract_calls == 1
    specialized = result["result"].specialized
    assert specialized is not None
    assert specialized.extractor == "contract_terms"
    assert len(specialized.parties) == 1
    assert specialized.parties[0].name == "Northstar Hosting Ltd."


@pytest.mark.asyncio
async def test_generic_route_never_calls_contract_provider() -> None:
    generic_provider = _FakeGenericProvider(
        [GenericAnalysisCandidate(summary=_summary())]
    )
    state = _base_state("generic", generic_provider)
    # No contract_provider in state at all: if the graph tried to call it,
    # this would raise a KeyError, proving the route is never taken. See
    # test_technical_spec_graph.py for the technical_specification route,
    # which now takes its own specialized path (never the contract one).

    result = await run_analysis_graph(state)

    assert result["status"] == "completed"
    assert result["result"].specialized is None
    assert generic_provider.extract_calls == 1


@pytest.mark.asyncio
async def test_targeted_retry_repairs_only_invalid_contract_items() -> None:
    """Generic output is valid on the first pass; only the contract party is
    invalid (evidence not on the cited page). Only the contract provider's
    repair should be called."""
    generic_provider = _FakeGenericProvider(
        [GenericAnalysisCandidate(summary=_summary())]
    )
    bad_party = PartyCandidate(
        name="Bad", source_page=1, evidence="not present anywhere", confidence=0.5
    )
    fixed_party = _valid_party()
    contract_provider = _FakeContractProvider(
        [ContractExtractionCandidate(parties=[bad_party])],
        [ContractRepairCandidate(parties=[fixed_party])],
    )
    state = _base_state(
        "contract", generic_provider, contract_provider=contract_provider
    )

    result = await run_analysis_graph(state)

    assert result["status"] == "completed"
    assert generic_provider.extract_calls == 1
    assert generic_provider.repair_calls == 0
    assert contract_provider.extract_calls == 1
    assert contract_provider.repair_calls == 1
    specialized = result["result"].specialized
    assert specialized is not None
    assert [p.name for p in specialized.parties] == ["Northstar Hosting Ltd."]


@pytest.mark.asyncio
async def test_still_invalid_contract_item_after_retry_fails_safely() -> None:
    bad_party = PartyCandidate(
        name="Bad", source_page=1, evidence="not present anywhere", confidence=0.5
    )
    still_bad = PartyCandidate(
        name="Still bad", source_page=1, evidence="also not present", confidence=0.5
    )
    generic_provider = _FakeGenericProvider(
        [GenericAnalysisCandidate(summary=_summary())]
    )
    contract_provider = _FakeContractProvider(
        [ContractExtractionCandidate(parties=[bad_party])],
        [ContractRepairCandidate(parties=[still_bad])],
    )
    state = _base_state(
        "contract", generic_provider, contract_provider=contract_provider
    )

    result = await run_analysis_graph(state)

    assert result["status"] == "failed"
    assert result["result"] is None
    assert contract_provider.repair_calls == 1


@pytest.mark.asyncio
async def test_contract_allows_all_empty_categories() -> None:
    generic_provider = _FakeGenericProvider(
        [GenericAnalysisCandidate(summary=_summary())]
    )
    contract_provider = _FakeContractProvider([ContractExtractionCandidate()])
    state = _base_state(
        "contract", generic_provider, contract_provider=contract_provider
    )

    result = await run_analysis_graph(state)

    assert result["status"] == "completed"
    specialized = result["result"].specialized
    assert specialized is not None
    assert specialized.parties == ()
    assert specialized.obligations == ()
    assert specialized.payment_terms == ()
    assert specialized.clauses == ()
