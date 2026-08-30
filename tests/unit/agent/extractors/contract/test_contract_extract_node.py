"""Direct test for the extract_contract_terms node."""

import pytest

from agent.analysis.nodes.extract_contract_terms import extract_contract_terms
from agent.extractors.contract.provider import ProviderMetadata
from agent.extractors.contract.types import ContractExtractionCandidate, PartyCandidate


class _FakeContractProvider:
    def __init__(self, candidate: ContractExtractionCandidate) -> None:
        self._candidate = candidate
        self.extract_calls = 0

    async def extract(self, *, system_instruction, user_content):
        self.extract_calls += 1
        return self._candidate, ProviderMetadata(provider="fake", model="m")

    async def repair(self, **kwargs):
        raise AssertionError("extract node must not call repair")


@pytest.mark.asyncio
async def test_extract_contract_terms_populates_pending_items() -> None:
    party = PartyCandidate(
        name="Northstar Hosting Ltd.",
        source_page=1,
        evidence="Northstar Hosting Ltd.",
        confidence=0.9,
    )
    candidate = ContractExtractionCandidate(parties=[party])
    provider = _FakeContractProvider(candidate)
    state = {
        "status": "pending",
        "filename": "contract.pdf",
        "pages": [(1, "Northstar Hosting Ltd. is the Provider.")],
        "section_titles": [],
        "contract_provider": provider,
    }

    result = await extract_contract_terms(state)

    assert result["pending_parties"] == [party]
    assert result["pending_obligations"] == []
    assert result["valid_parties"] == []
    assert provider.extract_calls == 1


@pytest.mark.asyncio
async def test_extract_contract_terms_short_circuits_when_failed() -> None:
    assert await extract_contract_terms({"status": "failed"}) == {}
