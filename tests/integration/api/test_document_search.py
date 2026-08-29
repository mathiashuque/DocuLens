"""API integration tests for POST /api/documents/{id}/search.

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
    monkeypatch.setattr(
        "app.services.indexing._build_provider",
        lambda settings: FakeEmbeddingProvider(dimension=settings.dimension),
    )
    monkeypatch.setattr(
        "app.services.search.OpenAIEmbeddingProvider",
        lambda **kwargs: FakeEmbeddingProvider(dimension=kwargs["dimension"]),
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_and_index(client: TestClient, pages_text: list[str], filename: str) -> dict:
    data = _build_pdf(pages_text)
    response = client.post(
        DOCUMENTS_ENDPOINT, files={"file": (filename, data, "application/pdf")}
    )
    assert response.status_code == 201
    document = response.json()
    index_response = client.post(f"{DOCUMENTS_ENDPOINT}/{document['id']}/index")
    assert index_response.status_code == 201
    return document


def test_search_unknown_document_returns_404(client: TestClient) -> None:
    response = client.post(
        f"{DOCUMENTS_ENDPOINT}/{uuid.uuid4()}/search", json={"query": "hello"}
    )
    assert response.status_code == 404


def test_search_without_index_returns_404(client: TestClient) -> None:
    data = _build_pdf(["Some page text."])
    created = client.post(
        DOCUMENTS_ENDPOINT, files={"file": ("no_index.pdf", data, "application/pdf")}
    )
    document = created.json()

    response = client.post(
        f"{DOCUMENTS_ENDPOINT}/{document['id']}/search", json={"query": "hello"}
    )
    assert response.status_code == 404


def test_search_success_returns_ranked_results_with_provenance(
    client: TestClient,
) -> None:
    document = _create_and_index(
        client,
        ["Either party may terminate this agreement with sixty days written notice."],
        "contract.pdf",
    )

    response = client.post(
        f"{DOCUMENTS_ENDPOINT}/{document['id']}/search",
        json={"query": "termination notice period", "top_k": 3},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == document["id"]
    assert body["strategy"] == "vector_cosine_baseline"
    assert body["query"] == "termination notice period"
    assert len(body["results"]) >= 1
    result = body["results"][0]
    assert result["page_start"] >= 1
    assert result["page_end"] >= result["page_start"]
    assert result.get("text")
    assert "score" in result
    assert "vector" not in result and "embedding" not in result


def test_search_blank_query_returns_422(client: TestClient) -> None:
    document = _create_and_index(client, ["Some content."], "blank.pdf")

    response = client.post(
        f"{DOCUMENTS_ENDPOINT}/{document['id']}/search", json={"query": "   "}
    )
    assert response.status_code == 422


def test_search_top_k_out_of_bounds_returns_422(client: TestClient) -> None:
    document = _create_and_index(client, ["Some content."], "topk.pdf")

    response = client.post(
        f"{DOCUMENTS_ENDPOINT}/{document['id']}/search",
        json={"query": "content", "top_k": 0},
    )
    assert response.status_code == 422


def test_search_never_leaks_across_documents(client: TestClient) -> None:
    doc_a = _create_and_index(
        client, ["Alpha document about apples and oranges."], "a.pdf"
    )
    _create_and_index(client, ["Beta document about bananas and grapes."], "b.pdf")

    # Query with doc_b's own vocabulary; a closer vector exists in doc_b,
    # but the search is scoped to doc_a and must never return doc_b's text.
    response = client.post(
        f"{DOCUMENTS_ENDPOINT}/{doc_a['id']}/search",
        json={"query": "bananas and grapes"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["document_id"] == doc_a["id"]
    assert len(body["results"]) == 1
    text = body["results"][0]["text"].lower()
    assert "alpha" in text
    assert "banana" not in text and "grape" not in text
