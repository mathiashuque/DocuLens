"""API integration tests for POST /api/documents/{id}/index.

The embedding provider boundary is monkeypatched to the deterministic fake
adapter; no test in this module makes a network call or requires
credentials.
"""

import uuid
from collections.abc import Iterator

import pymupdf
import pytest
from app.main import app
from fastapi.testclient import TestClient

from retrieval.providers.fake_provider import FakeEmbeddingProvider

DOCUMENTS_ENDPOINT = "/api/documents"


def _build_pdf(pages_text: list[str]) -> bytes:
    document = pymupdf.open()
    for text_content in pages_text:
        page = document.new_page()
        if text_content:
            page.insert_text((72, 72), text_content)
    data = document.tobytes()
    document.close()
    return data


@pytest.fixture
def client(
    postgres_url: str, clean_tables: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _patch_fake_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.indexing._build_provider",
        lambda settings: FakeEmbeddingProvider(dimension=settings.dimension),
    )


def _create_document(client: TestClient, pages_text: list[str], filename: str) -> dict:
    data = _build_pdf(pages_text)
    response = client.post(
        DOCUMENTS_ENDPOINT, files={"file": (filename, data, "application/pdf")}
    )
    assert response.status_code == 201
    return response.json()


def test_index_unknown_document_returns_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_fake_provider(monkeypatch)
    response = client.post(f"{DOCUMENTS_ENDPOINT}/{uuid.uuid4()}/index")
    assert response.status_code == 404


def test_index_success_returns_201_with_metadata(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_fake_provider(monkeypatch)
    document = _create_document(client, ["Hello world, this is page one."], "a.pdf")

    response = client.post(f"{DOCUMENTS_ENDPOINT}/{document['id']}/index")

    assert response.status_code == 201
    body = response.json()
    assert body["document_id"] == document["id"]
    assert body["status"] == "completed"
    assert body["chunk_count"] >= 1
    assert body["embedding_provider"] == "openai"
    assert body["dimension"] == 1536
    assert "chunker_version" in body
    assert "created_at" in body


def test_index_is_idempotent_and_avoids_second_provider_call(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    call_count = 0
    real_init = FakeEmbeddingProvider.__init__

    def _counting_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal call_count
        call_count += 1
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(FakeEmbeddingProvider, "__init__", _counting_init)
    monkeypatch.setattr(
        "app.services.indexing._build_provider",
        lambda settings: FakeEmbeddingProvider(dimension=settings.dimension),
    )
    document = _create_document(client, ["Some content about widgets."], "b.pdf")

    first = client.post(f"{DOCUMENTS_ENDPOINT}/{document['id']}/index")
    assert first.status_code == 201
    assert call_count == 1

    second = client.post(f"{DOCUMENTS_ENDPOINT}/{document['id']}/index")
    assert second.status_code == 200
    assert call_count == 1  # no second provider construction/call
    assert second.json()["chunk_count"] == first.json()["chunk_count"]


def test_index_missing_embedding_key_returns_503(client: TestClient) -> None:
    # No monkeypatch of the provider builder and no API key set: the real
    # OpenAI adapter path is reached and must fail safely without network.
    import os

    os.environ.pop("OPENAI_API_KEY", None)
    document = _create_document(client, ["Some content."], "c.pdf")

    response = client.post(f"{DOCUMENTS_ENDPOINT}/{document['id']}/index")

    assert response.status_code == 503
