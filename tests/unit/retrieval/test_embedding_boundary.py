import pytest

from retrieval.embedding import EmbeddingProviderRequestError, validate_vectors
from retrieval.providers.openai_provider import OpenAIEmbeddingProvider


def test_validate_vectors_accepts_matching_count_and_dimension() -> None:
    validate_vectors([[0.1, 0.2], [0.3, 0.4]], expected_count=2, expected_dimension=2)


def test_validate_vectors_rejects_count_mismatch() -> None:
    with pytest.raises(EmbeddingProviderRequestError):
        validate_vectors([[0.1, 0.2]], expected_count=2, expected_dimension=2)


def test_validate_vectors_rejects_dimension_mismatch() -> None:
    with pytest.raises(EmbeddingProviderRequestError):
        validate_vectors([[0.1, 0.2, 0.3]], expected_count=1, expected_dimension=2)


def test_validate_vectors_rejects_non_finite_values() -> None:
    with pytest.raises(EmbeddingProviderRequestError):
        validate_vectors([[float("nan"), 0.2]], expected_count=1, expected_dimension=2)
    with pytest.raises(EmbeddingProviderRequestError):
        validate_vectors([[float("inf"), 0.2]], expected_count=1, expected_dimension=2)


def test_openai_provider_construction_never_reaches_network() -> None:
    # Constructing the adapter must not perform any I/O; the API key is
    # fake and no request is made in this test.
    provider = OpenAIEmbeddingProvider(
        api_key="sk-test-not-real",
        model="text-embedding-3-small",
        dimension=8,
        timeout_seconds=1.0,
        max_batch_size=4,
    )
    assert provider is not None


def test_openai_provider_requires_api_key() -> None:
    from retrieval.embedding import EmbeddingProviderUnavailableError

    with pytest.raises(EmbeddingProviderUnavailableError):
        OpenAIEmbeddingProvider(
            api_key="",
            model="text-embedding-3-small",
            dimension=8,
            timeout_seconds=1.0,
        )
