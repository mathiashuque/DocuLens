"""OpenAI embedding adapter.

Constructed lazily by the service layer only when an index/search actually
needs a provider; app import, health, upload, analysis, and GET endpoints
must work without an embedding key. Never logs input text, vectors, keys,
headers, or raw provider responses.
"""

import time

from openai import APIStatusError, APITimeoutError, AsyncOpenAI, OpenAIError

from retrieval.embedding import (
    EmbeddingBatch,
    EmbeddingProviderRequestError,
    EmbeddingProviderUnavailableError,
    EmbeddingVector,
    validate_vectors,
)

OPENAI_PROVIDER_NAME = "openai"

# Conservative default for `text-embedding-3-small`; see OpenAI's embeddings
# guide for current per-request batch/input limits at deployment time.
DEFAULT_MAX_BATCH_SIZE = 96
_MAX_RETRIES = 2

# Errors OpenAI's SDK raises for auth/quota/policy problems that a retry
# cannot fix; retrying would waste calls and budget.
_NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404, 422, 429}


class OpenAIEmbeddingProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        dimension: int,
        timeout_seconds: float,
        max_batch_size: int = DEFAULT_MAX_BATCH_SIZE,
    ) -> None:
        if not api_key:
            raise EmbeddingProviderUnavailableError(
                "Embedding provider is not configured."
            )
        if max_batch_size <= 0:
            raise EmbeddingProviderUnavailableError(
                "Embedding provider batch size must be positive."
            )
        self._model = model
        self._dimension = dimension
        self._max_batch_size = max_batch_size
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout_seconds)

    async def _create(self, inputs: list[str]) -> tuple[list[list[float]], int | None]:
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await self._client.embeddings.create(
                    model=self._model,
                    input=inputs,
                    dimensions=self._dimension,
                )
            except APIStatusError as exc:
                if exc.status_code in _NON_RETRYABLE_STATUS_CODES:
                    raise EmbeddingProviderRequestError(
                        "Embedding provider rejected the request.",
                        retryable=False,
                    ) from exc
                last_error = exc
                continue
            except APITimeoutError as exc:
                last_error = exc
                continue
            except OpenAIError as exc:
                raise EmbeddingProviderRequestError(
                    "Embedding provider call failed.", retryable=False
                ) from exc
            else:
                vectors = [item.embedding for item in response.data]
                usage = getattr(response, "usage", None)
                input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
                return vectors, input_tokens

        raise EmbeddingProviderRequestError(
            f"Embedding provider call failed after {_MAX_RETRIES + 1} attempts.",
            retryable=True,
        ) from last_error

    async def embed_documents(self, texts: list[str]) -> EmbeddingBatch:
        if not texts:
            return EmbeddingBatch(
                vectors=[],
                provider=OPENAI_PROVIDER_NAME,
                model=self._model,
                dimension=self._dimension,
            )
        if len(texts) > self._max_batch_size:
            raise EmbeddingProviderRequestError(
                f"Batch of {len(texts)} exceeds configured maximum of "
                f"{self._max_batch_size}.",
                retryable=False,
            )

        start = time.perf_counter()
        vectors, input_tokens = await self._create(texts)
        latency_ms = int((time.perf_counter() - start) * 1000)
        validate_vectors(
            vectors, expected_count=len(texts), expected_dimension=self._dimension
        )
        return EmbeddingBatch(
            vectors=vectors,
            provider=OPENAI_PROVIDER_NAME,
            model=self._model,
            dimension=self._dimension,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
        )

    async def embed_query(self, text: str) -> EmbeddingVector:
        start = time.perf_counter()
        vectors, input_tokens = await self._create([text])
        latency_ms = int((time.perf_counter() - start) * 1000)
        validate_vectors(vectors, expected_count=1, expected_dimension=self._dimension)
        return EmbeddingVector(
            vector=vectors[0],
            provider=OPENAI_PROVIDER_NAME,
            model=self._model,
            dimension=self._dimension,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
        )
