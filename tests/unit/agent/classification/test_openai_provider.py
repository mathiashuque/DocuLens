"""OpenAI adapter unit tests using an SDK transport mock — no network.

Verifies lazy client construction, request shape, safe error mapping, and
that a missing key never instantiates the SDK client.
"""

from unittest.mock import MagicMock

import pytest

from agent.classification.provider import ProviderRequestError, ProviderUnavailableError
from agent.classification.providers.openai_provider import OpenAIClassificationProvider
from agent.classification.types import ClassificationCandidate


def _candidate() -> ClassificationCandidate:
    return ClassificationCandidate.model_validate(
        {
            "document_type": "contract",
            "confidence": 0.9,
            "reason": "reason",
            "evidence": [{"page": 1, "text": "quote"}],
        }
    )


def test_missing_api_key_raises_without_constructing_client() -> None:
    with pytest.raises(ProviderUnavailableError):
        OpenAIClassificationProvider(
            api_key="", model="gpt-4o-mini", timeout_seconds=30.0, max_output_tokens=800
        )


def test_client_is_constructed_lazily(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAIClassificationProvider(
        api_key="key", model="gpt-4o-mini", timeout_seconds=30.0, max_output_tokens=800
    )

    assert provider._client is None  # not constructed at instantiation time


@pytest.mark.asyncio
async def test_classify_sends_expected_request_shape() -> None:
    provider = OpenAIClassificationProvider(
        api_key="key", model="gpt-4o-mini", timeout_seconds=30.0, max_output_tokens=800
    )

    fake_response = MagicMock()
    fake_response.output_parsed = _candidate()
    fake_response.usage.input_tokens = 100
    fake_response.usage.output_tokens = 50

    fake_client = MagicMock()
    fake_client.responses.parse.return_value = fake_response
    provider._client = fake_client

    candidate, metadata = await provider.classify(
        system_instruction="system", user_content="user"
    )

    assert candidate.document_type == "contract"
    assert metadata.provider == "openai"
    assert metadata.model == "gpt-4o-mini"
    assert metadata.input_tokens == 100
    assert metadata.output_tokens == 50

    _, kwargs = fake_client.responses.parse.call_args
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["text_format"] is ClassificationCandidate
    assert kwargs["input"][0] == {"role": "system", "content": "system"}
    assert kwargs["input"][1] == {"role": "user", "content": "user"}
    assert kwargs["max_output_tokens"] == 800


@pytest.mark.asyncio
async def test_none_parsed_output_raises_retryable_error() -> None:
    provider = OpenAIClassificationProvider(
        api_key="key", model="gpt-4o-mini", timeout_seconds=30.0, max_output_tokens=800
    )
    fake_response = MagicMock()
    fake_response.output_parsed = None
    fake_client = MagicMock()
    fake_client.responses.parse.return_value = fake_response
    provider._client = fake_client

    with pytest.raises(ProviderRequestError) as exc_info:
        await provider.classify(system_instruction="s", user_content="u")

    assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_auth_error_maps_to_non_retryable_provider_error() -> None:
    from openai import APIStatusError

    provider = OpenAIClassificationProvider(
        api_key="key", model="gpt-4o-mini", timeout_seconds=30.0, max_output_tokens=800
    )

    auth_error = APIStatusError(
        "unauthorized",
        response=MagicMock(status_code=401, headers={}),
        body=None,
    )
    fake_client = MagicMock()
    fake_client.responses.parse.side_effect = auth_error
    provider._client = fake_client

    with pytest.raises(ProviderRequestError) as exc_info:
        await provider.classify(system_instruction="s", user_content="u")

    assert exc_info.value.retryable is False


@pytest.mark.asyncio
async def test_timeout_maps_to_retryable_provider_error() -> None:
    from openai import APITimeoutError

    provider = OpenAIClassificationProvider(
        api_key="key", model="gpt-4o-mini", timeout_seconds=30.0, max_output_tokens=800
    )

    fake_client = MagicMock()
    fake_client.responses.parse.side_effect = APITimeoutError(request=MagicMock())
    provider._client = fake_client

    with pytest.raises(ProviderRequestError) as exc_info:
        await provider.classify(system_instruction="s", user_content="u")

    assert exc_info.value.retryable is True
