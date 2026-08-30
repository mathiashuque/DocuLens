"""Grounded QA OpenAI adapter unit tests using an SDK transport mock — no
network. Mirrors analysis's own adapter test shape."""

from unittest.mock import MagicMock

import pytest

from agent.grounded_qa.provider import ProviderUnavailableError
from agent.grounded_qa.providers.openai_provider import OpenAIGroundedQaProvider
from agent.grounded_qa.types import GroundedAnswerCandidate


def _candidate() -> GroundedAnswerCandidate:
    return GroundedAnswerCandidate(status="answered", answer="Yes.", citations=[])


def test_missing_api_key_raises_without_constructing_client() -> None:
    with pytest.raises(ProviderUnavailableError):
        OpenAIGroundedQaProvider(
            api_key="", model="gpt-4o-mini", timeout_seconds=30.0, max_output_tokens=800
        )


def test_client_is_constructed_lazily() -> None:
    provider = OpenAIGroundedQaProvider(
        api_key="key", model="gpt-4o-mini", timeout_seconds=30.0, max_output_tokens=800
    )
    assert provider._client is None


@pytest.mark.asyncio
async def test_answer_sends_expected_request_shape() -> None:
    provider = OpenAIGroundedQaProvider(
        api_key="key", model="gpt-4o-mini", timeout_seconds=30.0, max_output_tokens=800
    )
    fake_response = MagicMock()
    fake_response.output_parsed = _candidate()
    fake_response.usage.input_tokens = 300
    fake_response.usage.output_tokens = 50
    fake_client = MagicMock()
    fake_client.responses.parse.return_value = fake_response
    provider._client = fake_client

    candidate, metadata = await provider.answer(
        system_instruction="system", user_content="user"
    )

    assert candidate.status == "answered"
    assert metadata.provider == "openai"
    _, kwargs = fake_client.responses.parse.call_args
    assert kwargs["text_format"] is GroundedAnswerCandidate
    assert kwargs["max_output_tokens"] == 800


@pytest.mark.asyncio
async def test_repair_uses_same_candidate_schema() -> None:
    provider = OpenAIGroundedQaProvider(
        api_key="key", model="gpt-4o-mini", timeout_seconds=30.0, max_output_tokens=800
    )
    fake_response = MagicMock()
    fake_response.output_parsed = GroundedAnswerCandidate(
        status="insufficient_evidence", answer="no evidence", citations=[]
    )
    fake_response.usage = None
    fake_client = MagicMock()
    fake_client.responses.parse.return_value = fake_response
    provider._client = fake_client

    candidate, _metadata = await provider.repair(
        system_instruction="system", user_content="user"
    )

    assert candidate.status == "insufficient_evidence"
    _, kwargs = fake_client.responses.parse.call_args
    assert kwargs["text_format"] is GroundedAnswerCandidate
