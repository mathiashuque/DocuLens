"""OpenAI structured-output adapter for contract extraction.

Mirrors `agent.analysis.providers.openai_provider`: lazy client construction
(never at import time), and the actual SDK call/exception mapping shared via
`agent.llm.structured_openai.complete_structured`.
"""

from agent.extractors.contract.provider import (
    ProviderMetadata,
    ProviderUnavailableError,
)
from agent.extractors.contract.types import (
    ContractExtractionCandidate,
    ContractRepairCandidate,
)
from agent.llm.structured_openai import complete_structured


class OpenAIContractProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> None:
        if not api_key:
            raise ProviderUnavailableError("Contract provider is not configured.")
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
                    "Contract provider dependency is unavailable."
                ) from exc
            self._client = OpenAI(api_key=self._api_key, timeout=self._timeout_seconds)
        return self._client

    async def extract(
        self, *, system_instruction: str, user_content: str
    ) -> tuple[ContractExtractionCandidate, ProviderMetadata]:
        client = self._get_client()
        return await complete_structured(
            client,
            model=self._model,
            system_instruction=system_instruction,
            user_content=user_content,
            output_type=ContractExtractionCandidate,
            max_output_tokens=self._max_output_tokens,
            provider_name="openai",
        )

    async def repair(
        self, *, system_instruction: str, user_content: str
    ) -> tuple[ContractRepairCandidate, ProviderMetadata]:
        client = self._get_client()
        return await complete_structured(
            client,
            model=self._model,
            system_instruction=system_instruction,
            user_content=user_content,
            output_type=ContractRepairCandidate,
            max_output_tokens=self._max_output_tokens,
            provider_name="openai",
        )
