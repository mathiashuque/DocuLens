"""Provider-agnostic embedding boundary.

Chunking, indexing, search, and evaluation code depend only on this module.
Concrete provider SDK imports and payload details stay inside adapters
under `retrieval/providers/`, mirroring `agent/classification/provider.py`.
"""

import math
from dataclasses import dataclass
from typing import Protocol


class EmbeddingProviderUnavailableError(Exception):
    """The configured embedding provider is missing, misconfigured, or
    unreachable (e.g. no API key). Maps to a safe HTTP 503 at the API
    boundary. Never carries key material, headers, or endpoint details."""


class EmbeddingProviderRequestError(Exception):
    """An embedding call failed after allowed retries (timeout, transport
    error, quota/policy rejection, or a returned vector count/dimension
    mismatch). Maps to a safe HTTP 502 at the API boundary."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class EmbeddingVector:
    """One embedded query's result plus safe call metadata."""

    vector: list[float]
    provider: str
    model: str
    dimension: int
    latency_ms: int | None = None
    input_tokens: int | None = None


@dataclass(frozen=True)
class EmbeddingBatch:
    """Embedded document chunks, order-preserved with the input list."""

    vectors: list[list[float]]
    provider: str
    model: str
    dimension: int
    latency_ms: int | None = None
    input_tokens: int | None = None


class EmbeddingProvider(Protocol):
    """One embedding operation family: bounded batches of chunk text in,
    order-preserved vectors out; a single query embedded on demand.

    Implementations must raise `EmbeddingProviderUnavailableError` for
    configuration problems and `EmbeddingProviderRequestError` for
    exhausted/transport/malformed-output failures. They must never log
    input text, vectors, keys, headers, or raw provider responses.
    """

    async def embed_documents(self, texts: list[str]) -> EmbeddingBatch: ...

    async def embed_query(self, text: str) -> EmbeddingVector: ...


def validate_vectors(
    vectors: list[list[float]], *, expected_count: int, expected_dimension: int
) -> None:
    """Validate a batch of vectors before persistence or query execution.

    Raises `EmbeddingProviderRequestError` (non-retryable: the caller
    already exhausted retries by the time this check runs) if the count,
    dimension, or any value is invalid.
    """
    if len(vectors) != expected_count:
        raise EmbeddingProviderRequestError(
            f"Embedding provider returned {len(vectors)} vectors for "
            f"{expected_count} inputs."
        )
    for vector in vectors:
        if len(vector) != expected_dimension:
            raise EmbeddingProviderRequestError(
                f"Embedding provider returned dimension {len(vector)}, "
                f"expected {expected_dimension}."
            )
        for value in vector:
            if not _is_finite(value):
                raise EmbeddingProviderRequestError(
                    "Embedding provider returned a non-finite vector value."
                )


def _is_finite(value: float) -> bool:
    return math.isfinite(value)
