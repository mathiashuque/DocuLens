"""OpenAI structured-output adapter.

Uses the Responses API's `responses.parse(..., text_format=<PydanticModel>)`
so the SDK handles schema conversion and parsing. The client is constructed
lazily (first call), never at import time, so app import/health/tests never
require an API key. The actual SDK call/exception-mapping is shared with the
analysis adapter via `agent.llm.structured_openai`.
"""

from agent.classification.provider import ProviderMetadata, ProviderUnavailableError
from agent.classification.types import ClassificationCandidate
from agent.llm.structured_openai import complete_structured


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
        client = self._get_client()
        return await complete_structured(
            client,
            model=self._model,
            system_instruction=system_instruction,
            user_content=user_content,
            output_type=ClassificationCandidate,
            max_output_tokens=self._max_output_tokens,
            provider_name="openai",
        )
