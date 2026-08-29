"""Direct test for the retry_invalid_subset node."""

import pytest

from agent.analysis.nodes.retry_invalid_subset import retry_invalid_subset
from agent.analysis.provider import ProviderMetadata, ProviderRequestError
from agent.analysis.types import FindingCandidate, RepairCandidate
from agent.classification.context import ClassificationContext, PageExcerpt


def _context() -> ClassificationContext:
    return ClassificationContext(
        filename="doc.pdf",
        excerpts=[PageExcerpt(page=1, text="hello world")],
        section_titles=[],
        budget_chars=1000,
        truncated=False,
    )


class _FakeProvider:
    def __init__(self, outcome):
        self._outcome = outcome
        self.calls = 0

    async def extract(self, **kwargs):
        raise AssertionError("retry node must call repair, not extract")

    async def repair(self, *, system_instruction, user_content):
        self.calls += 1
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome, ProviderMetadata(provider="fake", model="m")


@pytest.mark.asyncio
async def test_retry_node_sends_only_invalid_item_descriptions() -> None:
    repaired = RepairCandidate(
        findings=[
            FindingCandidate(
                title="Fixed",
                description="d",
                category="c",
                importance="low",
                source_page=1,
                evidence="hello world",
                confidence=0.5,
            )
        ]
    )
    provider = _FakeProvider(repaired)
    state = {
        "context": _context(),
        "provider": provider,
        "invalid_items": [
            {"kind": "finding", "description": "Bad thing", "error": "bad"}
        ],
        "retry_count": 0,
    }

    result = await retry_invalid_subset(state)

    assert result["pending_findings"] == repaired.findings
    assert result["retry_count"] == 1
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_retry_node_fails_safely_on_provider_error() -> None:
    provider = _FakeProvider(ProviderRequestError("boom", retryable=False))
    state = {
        "context": _context(),
        "provider": provider,
        "invalid_items": [{"kind": "finding", "description": "Bad", "error": "bad"}],
        "retry_count": 0,
    }

    result = await retry_invalid_subset(state)

    assert result["status"] == "failed"
    assert result["retry_count"] == 1
