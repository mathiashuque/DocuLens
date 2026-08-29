"""Analysis OpenAI adapter unit tests using an SDK transport mock — no
network. Mirrors classification's own adapter test shape."""

from unittest.mock import MagicMock

import pytest

from agent.analysis.provider import ProviderUnavailableError
from agent.analysis.providers.openai_provider import OpenAIAnalysisProvider
from agent.analysis.types import DocumentSummaryCandidate, GenericAnalysisCandidate


def _candidate() -> GenericAnalysisCandidate:
    return GenericAnalysisCandidate(
        summary=DocumentSummaryCandidate(purpose="p", summary="s"),
        findings=[],
        important_dates=[],
        risks=[],
    )


def test_missing_api_key_raises_without_constructing_client() -> None:
    with pytest.raises(ProviderUnavailableError):
        OpenAIAnalysisProvider(
            api_key="",
            model="gpt-4o-mini",
            timeout_seconds=60.0,
            max_output_tokens=2000,
        )


def test_client_is_constructed_lazily() -> None:
    provider = OpenAIAnalysisProvider(
        api_key="key", model="gpt-4o-mini", timeout_seconds=60.0, max_output_tokens=2000
    )
    assert provider._client is None


@pytest.mark.asyncio
async def test_extract_sends_expected_request_shape() -> None:
    provider = OpenAIAnalysisProvider(
        api_key="key", model="gpt-4o-mini", timeout_seconds=60.0, max_output_tokens=2000
    )
    fake_response = MagicMock()
    fake_response.output_parsed = _candidate()
    fake_response.usage.input_tokens = 500
    fake_response.usage.output_tokens = 150
    fake_client = MagicMock()
    fake_client.responses.parse.return_value = fake_response
    provider._client = fake_client

    candidate, metadata = await provider.extract(
        system_instruction="system", user_content="user"
    )

    assert candidate.summary.purpose == "p"
    assert metadata.provider == "openai"
    assert metadata.input_tokens == 500

    _, kwargs = fake_client.responses.parse.call_args
    assert kwargs["text_format"] is GenericAnalysisCandidate
    assert kwargs["max_output_tokens"] == 2000


@pytest.mark.asyncio
async def test_repair_uses_repair_candidate_schema() -> None:
    from agent.analysis.types import RepairCandidate

    provider = OpenAIAnalysisProvider(
        api_key="key", model="gpt-4o-mini", timeout_seconds=60.0, max_output_tokens=2000
    )
    fake_response = MagicMock()
    fake_response.output_parsed = RepairCandidate()
    fake_response.usage = None
    fake_client = MagicMock()
    fake_client.responses.parse.return_value = fake_response
    provider._client = fake_client

    candidate, _metadata = await provider.repair(
        system_instruction="system", user_content="user"
    )

    assert candidate.findings == []
    _, kwargs = fake_client.responses.parse.call_args
    assert kwargs["text_format"] is RepairCandidate
