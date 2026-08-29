"""Direct test for the extract_technical_spec_requirements node."""

import pytest

from agent.analysis.nodes.extract_technical_spec_requirements import (
    extract_technical_spec_requirements,
)
from agent.extractors.technical_spec.provider import ProviderMetadata
from agent.extractors.technical_spec.types import (
    RequirementCandidate,
    TechnicalSpecExtractionCandidate,
)


class _FakeTechnicalSpecProvider:
    def __init__(self, candidate: TechnicalSpecExtractionCandidate) -> None:
        self._candidate = candidate
        self.extract_calls = 0

    async def extract(self, *, system_instruction, user_content):
        self.extract_calls += 1
        return self._candidate, ProviderMetadata(provider="fake", model="m")

    async def repair(self, **kwargs):
        raise AssertionError("extract node must not call repair")


@pytest.mark.asyncio
async def test_extract_technical_spec_requirements_populates_pending_items() -> None:
    requirement = RequirementCandidate(
        category="functional",
        statement="Revoke active sessions",
        source_page=1,
        evidence="The service shall allow administrators to revoke active sessions.",
        confidence=0.9,
    )
    candidate = TechnicalSpecExtractionCandidate(requirements=[requirement])
    provider = _FakeTechnicalSpecProvider(candidate)
    state = {
        "status": "pending",
        "filename": "spec.pdf",
        "pages": [
            (1, "The service shall allow administrators to revoke active sessions.")
        ],
        "section_titles": [],
        "technical_spec_provider": provider,
    }

    result = await extract_technical_spec_requirements(state)

    assert result["pending_requirements"] == [requirement]
    assert result["pending_constraints"] == []
    assert result["valid_requirements"] == []
    assert provider.extract_calls == 1


@pytest.mark.asyncio
async def test_extract_technical_spec_requirements_applies_category_precedence() -> (
    None
):
    """Two candidates citing the same evidence under different categories
    should collapse to the higher-precedence one before validation."""
    evidence = "The service shall encrypt data and allow session revocation."
    security_version = RequirementCandidate(
        category="security",
        statement="Encrypt data",
        source_page=1,
        evidence=evidence,
        confidence=0.9,
    )
    functional_version = RequirementCandidate(
        category="functional",
        statement="Revoke sessions",
        source_page=1,
        evidence=evidence,
        confidence=0.5,
    )
    candidate = TechnicalSpecExtractionCandidate(
        requirements=[functional_version, security_version]
    )
    provider = _FakeTechnicalSpecProvider(candidate)
    state = {
        "status": "pending",
        "filename": "spec.pdf",
        "pages": [(1, evidence)],
        "section_titles": [],
        "technical_spec_provider": provider,
    }

    result = await extract_technical_spec_requirements(state)

    assert len(result["pending_requirements"]) == 1
    assert result["pending_requirements"][0].category == "security"


@pytest.mark.asyncio
async def test_extract_technical_spec_requirements_short_circuits_when_failed() -> None:
    assert await extract_technical_spec_requirements({"status": "failed"}) == {}
