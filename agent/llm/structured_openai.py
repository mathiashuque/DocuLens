"""Shared OpenAI Responses-API structured-completion call.

Uses `responses.parse(..., text_format=<PydanticModel>)` so the SDK handles
schema conversion and parsing. Takes an already-constructed client; each
capability's provider class still owns lazy client construction so tests can
inject a fake client via that provider's own `_client` attribute.
"""

import time
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from agent.classification.provider import (
    ProviderMetadata,
    ProviderRequestError,
    ProviderUnavailableError,
)

T = TypeVar("T", bound=BaseModel)


async def complete_structured(
    client: object,
    *,
    model: str,
    system_instruction: str,
    user_content: str,
    output_type: type[T],
    max_output_tokens: int,
    provider_name: str = "openai",
) -> tuple[T, ProviderMetadata]:
    try:
        from openai import APIError, APIStatusError, APITimeoutError
    except ImportError as exc:  # pragma: no cover - dependency always installed
        raise ProviderUnavailableError("Provider dependency is unavailable.") from exc

    started = time.monotonic()
    try:
        response = client.responses.parse(  # type: ignore[attr-defined]
            model=model,
            input=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ],
            text_format=output_type,
            max_output_tokens=max_output_tokens,
        )
    except APITimeoutError as exc:
        raise ProviderRequestError(
            "Provider request timed out.", retryable=True
        ) from exc
    except APIStatusError as exc:
        status_code = getattr(exc, "status_code", None)
        if status_code in (401, 403, 429):
            raise ProviderRequestError(
                "Provider rejected the request.", retryable=False
            ) from exc
        raise ProviderRequestError("Provider request failed.", retryable=True) from exc
    except APIError as exc:
        raise ProviderRequestError("Provider request failed.", retryable=True) from exc

    latency_ms = int((time.monotonic() - started) * 1000)
    candidate = response.output_parsed
    if candidate is None:
        raise ProviderRequestError(
            "Provider returned no parsed result.", retryable=True
        )
    try:
        validated = output_type.model_validate(candidate)
    except ValidationError as exc:
        raise ProviderRequestError(
            "Provider returned an invalid structured result.", retryable=True
        ) from exc

    usage = getattr(response, "usage", None)
    metadata = ProviderMetadata(
        provider=provider_name,
        model=model,
        latency_ms=latency_ms,
        input_tokens=getattr(usage, "input_tokens", None) if usage else None,
        output_tokens=getattr(usage, "output_tokens", None) if usage else None,
    )
    return validated, metadata
