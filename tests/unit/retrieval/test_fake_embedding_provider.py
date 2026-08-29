import math

import pytest

from retrieval.providers.fake_provider import FakeEmbeddingProvider


@pytest.mark.asyncio
async def test_embed_documents_preserves_order_and_dimension() -> None:
    provider = FakeEmbeddingProvider(dimension=8)
    batch = await provider.embed_documents(["alpha beta", "gamma delta", "alpha beta"])

    assert len(batch.vectors) == 3
    assert all(len(v) == 8 for v in batch.vectors)
    assert batch.vectors[0] == batch.vectors[2]  # identical text -> identical vector
    assert batch.dimension == 8
    assert all(math.isfinite(x) for v in batch.vectors for x in v)


@pytest.mark.asyncio
async def test_embed_query_deterministic() -> None:
    provider = FakeEmbeddingProvider(dimension=4)
    first = await provider.embed_query("hello world")
    second = await provider.embed_query("hello world")

    assert first.vector == second.vector
    assert first.dimension == 4
    assert first.provider == "fake"


@pytest.mark.asyncio
async def test_similar_text_ranks_closer_than_dissimilar_text() -> None:
    provider = FakeEmbeddingProvider(dimension=32)
    base = await provider.embed_query("termination notice sixty days")
    similar = await provider.embed_documents(["termination notice sixty day period"])
    dissimilar = await provider.embed_documents(["unrelated payment schedule amount"])

    def cosine(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b, strict=True))

    assert cosine(base.vector, similar.vectors[0]) > cosine(
        base.vector, dissimilar.vectors[0]
    )


def test_rejects_non_positive_dimension() -> None:
    with pytest.raises(ValueError):
        FakeEmbeddingProvider(dimension=0)
