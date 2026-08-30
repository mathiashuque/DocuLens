"""Deterministic fake embedding provider for tests and normal evaluation.

Normal tests and CI must never construct a real provider client or reach
the network. This adapter produces stable, deterministic vectors from input
text using a hash-based projection, so identical text always yields an
identical vector and semantically similar fixture text can be crafted to
rank predictably in retrieval tests and the baseline evaluation.
"""

import hashlib
import time

from retrieval.embedding import EmbeddingBatch, EmbeddingVector

FAKE_PROVIDER_NAME = "fake"


class FakeEmbeddingProvider:
    """First-class deterministic double for `EmbeddingProvider`.

    Not a test-only mock object: it is a real, complete implementation of
    the protocol, usable directly by the evaluation runner for CI-safe,
    reproducible baseline measurement.
    """

    def __init__(self, *, dimension: int = 16, model: str = "fake-hash-v1") -> None:
        if dimension <= 0:
            raise ValueError("dimension must be positive.")
        self.dimension = dimension
        self.model = model

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        normalized = text.lower().split()
        if not normalized:
            return vector
        for token in normalized:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for i in range(self.dimension):
                # Map two digest bytes per dimension into a signed float in
                # [-1, 1], accumulated per token so word overlap between
                # texts increases cosine similarity, unlike a single fixed
                # per-word slot.
                byte_pair = (
                    digest[(2 * i) % len(digest)] + digest[(2 * i + 1) % len(digest)]
                )
                vector[i] += (byte_pair / 255.0) - 1.0
        norm = sum(v * v for v in vector) ** 0.5
        if norm == 0:
            return vector
        return [v / norm for v in vector]

    async def embed_documents(self, texts: list[str]) -> EmbeddingBatch:
        start = time.perf_counter()
        vectors = [self._embed(text) for text in texts]
        latency_ms = int((time.perf_counter() - start) * 1000)
        return EmbeddingBatch(
            vectors=vectors,
            provider=FAKE_PROVIDER_NAME,
            model=self.model,
            dimension=self.dimension,
            latency_ms=latency_ms,
            input_tokens=sum(len(t.split()) for t in texts),
        )

    async def embed_query(self, text: str) -> EmbeddingVector:
        start = time.perf_counter()
        vector = self._embed(text)
        latency_ms = int((time.perf_counter() - start) * 1000)
        return EmbeddingVector(
            vector=vector,
            provider=FAKE_PROVIDER_NAME,
            model=self.model,
            dimension=self.dimension,
            latency_ms=latency_ms,
            input_tokens=len(text.split()),
        )
