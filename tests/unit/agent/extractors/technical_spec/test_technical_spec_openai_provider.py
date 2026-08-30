"""Technical-spec OpenAI adapter unit tests using an SDK transport mock —
no network. Mirrors `agent.extractors.contract.providers.openai_provider`'s
own test."""

from unittest.mock import MagicMock

import pytest

from agent.extractors.technical_spec.provider import ProviderUnavailableError
from agent.extractors.technical_spec.providers.openai_provider import (
    OpenAITechnicalSpecProvider,
)
from agent.extractors.technical_spec.types import (
    TechnicalSpecExtractionCandidate,
    TechnicalSpecRepairCandidate,
)


def test_missing_api_key_raises_without_constructing_client() -> None:
    with pytest.raises(ProviderUnavailableError):
        OpenAITechnicalSpecProvider(
            api_key="",
            model="gpt-4o-mini",
            timeout_seconds=60.0,
            max_output_tokens=2000,
        )


def test_client_is_constructed_lazily() -> None:
    provider = OpenAITechnicalSpecProvider(
        api_key="key", model="gpt-4o-mini", timeout_seconds=60.0, max_output_tokens=2000
    )
    assert provider._client is None


@pytest.mark.asyncio
async def test_extract_sends_expected_request_shape() -> None:
    provider = OpenAITechnicalSpecProvider(
        api_key="key", model="gpt-4o-mini", timeout_seconds=60.0, max_output_tokens=2000
    )
    fake_response = MagicMock()
    fake_response.output_parsed = TechnicalSpecExtractionCandidate()
    fake_response.usage.input_tokens = 500
    fake_response.usage.output_tokens = 150
    fake_client = MagicMock()
    fake_client.responses.parse.return_value = fake_response
    provider._client = fake_client

    candidate, metadata = await provider.extract(
        system_instruction="system", user_content="user"
    )

    assert candidate.requirements == []
    assert metadata.provider == "openai"
    assert metadata.input_tokens == 500

    _, kwargs = fake_client.responses.parse.call_args
    assert kwargs["text_format"] is TechnicalSpecExtractionCandidate
    assert kwargs["max_output_tokens"] == 2000


@pytest.mark.asyncio
async def test_repair_uses_repair_candidate_schema() -> None:
    provider = OpenAITechnicalSpecProvider(
        api_key="key", model="gpt-4o-mini", timeout_seconds=60.0, max_output_tokens=2000
    )
    fake_response = MagicMock()
    fake_response.output_parsed = TechnicalSpecRepairCandidate()
    fake_response.usage = None
    fake_client = MagicMock()
    fake_client.responses.parse.return_value = fake_response
    provider._client = fake_client

    candidate, _metadata = await provider.repair(
        system_instruction="system", user_content="user"
    )

    assert candidate.requirements == []
    _, kwargs = fake_client.responses.parse.call_args
    assert kwargs["text_format"] is TechnicalSpecRepairCandidate
