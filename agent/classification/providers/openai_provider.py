"""OpenAI structured-output adapter.

Uses the Responses API's `responses.parse(..., text_format=<PydanticModel>)`
so the SDK handles schema conversion and parsing. The client is constructed
lazily (first call), never at import time, so app import/health/tests never
require an API key.
"""

import time

from pydantic import ValidationError

from agent.classification.provider import (
    ProviderMetadata,
    ProviderRequestError,
    ProviderUnavailableError,
)
from agent.classification.types import ClassificationCandidate


class OpenAIClassificationProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> None:
        if not api_key:
            raise ProviderUnavailableError("Classification provider is not configured.")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._client = None  # constructed lazily on first call

    def _get_client(self):  # type: ignore[no-untyped-def]
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - dependency always installed
                raise ProviderUnavailableError(
                    "Classification provider dependency is unavailable."
                ) from exc
            self._client = OpenAI(api_key=self._api_key, timeout=self._timeout_seconds)
        return self._client

    async def classify(
        self, *, system_instruction: str, user_content: str
    ) -> tuple[ClassificationCandidate, ProviderMetadata]:
        try:
            from openai import APIError, APIStatusError, APITimeoutError
        except ImportError as exc:  # pragma: no cover - dependency always installed
            raise ProviderUnavailableError(
                "Classification provider dependency is unavailable."
            ) from exc

        client = self._get_client()
        started = time.monotonic()
        try:
            response = client.responses.parse(
                model=self._model,
                input=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_content},
                ],
                text_format=ClassificationCandidate,
                max_output_tokens=self._max_output_tokens,
            )
        except APITimeoutError as exc:
            raise ProviderRequestError(
                "Classification provider timed out.", retryable=True
            ) from exc
        except APIStatusError as exc:
            status_code = getattr(exc, "status_code", None)
            if status_code in (401, 403, 429):
                raise ProviderRequestError(
                    "Classification provider rejected the request.", retryable=False
                ) from exc
            raise ProviderRequestError(
                "Classification provider request failed.", retryable=True
            ) from exc
        except APIError as exc:
            raise ProviderRequestError(
                "Classification provider request failed.", retryable=True
            ) from exc

        latency_ms = int((time.monotonic() - started) * 1000)
        candidate = response.output_parsed
        if candidate is None:
            raise ProviderRequestError(
                "Classification provider returned no parsed result.", retryable=True
            )
        try:
            validated = ClassificationCandidate.model_validate(candidate)
        except ValidationError as exc:
            raise ProviderRequestError(
                "Classification provider returned an invalid structured result.",
                retryable=True,
            ) from exc

        usage = getattr(response, "usage", None)
        metadata = ProviderMetadata(
            provider="openai",
            model=self._model,
            latency_ms=latency_ms,
            input_tokens=getattr(usage, "input_tokens", None) if usage else None,
            output_tokens=getattr(usage, "output_tokens", None) if usage else None,
        )
        return validated, metadata
