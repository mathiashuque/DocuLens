"""API integration tests for POST/GET /api/documents/{id}/classification.

The provider boundary is monkeypatched to a fake in-process implementation;
no test in this module makes a network call or requires credentials.
"""

from collections.abc import Iterator
from typing import Any

import pymupdf
import pytest
from app.main import app
from fastapi.testclient import TestClient

from agent.classification.provider import ProviderMetadata, ProviderUnavailableError
from agent.classification.types import ClassificationCandidate

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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_document(client: TestClient, pages_text: list[str], filename: str) -> Any:
    data = _build_pdf(pages_text)
    response = client.post(
        DOCUMENTS_ENDPOINT, files={"file": (filename, data, "application/pdf")}
    )
    assert response.status_code == 201
    return response.json()


class _FakeProvider:
    def __init__(self, candidate: ClassificationCandidate) -> None:
        self._candidate = candidate
        self.calls = 0

    async def classify(
        self, *, system_instruction: str, user_content: str
    ) -> tuple[ClassificationCandidate, ProviderMetadata]:
        self.calls += 1
        return self._candidate, ProviderMetadata(
            provider="openai", model="gpt-4o-mini-test", latency_ms=5
        )


def _patch_provider(
    monkeypatch: pytest.MonkeyPatch, page_text: str, document_type: str = "contract"
) -> _FakeProvider:
    candidate = ClassificationCandidate.model_validate(
        {
            "document_type": document_type,
            "confidence": 0.9,
            "reason": "Defines parties and obligations.",
            "evidence": [{"page": 1, "text": page_text}],
        }
    )
    provider = _FakeProvider(candidate)
    monkeypatch.setattr(
        "app.services.classification._build_provider", lambda settings: provider
    )
    return provider


def test_post_returns_201_with_typed_shape(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    page_text = "This Agreement is entered into by the parties."
    created = _create_document(client, [page_text], "contract.pdf")
    provider = _patch_provider(monkeypatch, page_text)

    response = client.post(f"{DOCUMENTS_ENDPOINT}/{created['id']}/classification")

    assert response.status_code == 201
    body = response.json()
    assert body["document_id"] == created["id"]
    assert body["document_type"] == "contract"
    assert body["status"] == "completed"
    assert body["provider"] == "openai"
    assert body["evidence"][0]["page"] == 1
    assert provider.calls == 1


def test_repeated_post_reuses_result_without_second_provider_call(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    page_text = "This Agreement is entered into by the parties."
    created = _create_document(client, [page_text], "contract.pdf")
    provider = _patch_provider(monkeypatch, page_text)

    first = client.post(f"{DOCUMENTS_ENDPOINT}/{created['id']}/classification")
    second = client.post(f"{DOCUMENTS_ENDPOINT}/{created['id']}/classification")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert provider.calls == 1


def test_get_returns_latest_completed_without_invoking_provider(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    page_text = "This Agreement is entered into by the parties."
    created = _create_document(client, [page_text], "contract.pdf")
    provider = _patch_provider(monkeypatch, page_text)
    client.post(f"{DOCUMENTS_ENDPOINT}/{created['id']}/classification")

    def _fail(settings: object) -> object:
        raise AssertionError("GET must never invoke a provider")

    monkeypatch.setattr("app.services.classification._build_provider", _fail)

    response = client.get(f"{DOCUMENTS_ENDPOINT}/{created['id']}/classification")

    assert response.status_code == 200
    assert response.json()["document_type"] == "contract"
    assert provider.calls == 1


def test_get_returns_404_when_no_completed_classification_exists(
    client: TestClient,
) -> None:
    created = _create_document(client, ["Some plain body text."], "doc.pdf")

    response = client.get(f"{DOCUMENTS_ENDPOINT}/{created['id']}/classification")

    assert response.status_code == 404


def test_post_unknown_document_returns_404(client: TestClient) -> None:
    response = client.post(
        f"{DOCUMENTS_ENDPOINT}/00000000-0000-0000-0000-000000000000/classification"
    )

    assert response.status_code == 404


def test_get_unknown_document_returns_404(client: TestClient) -> None:
    response = client.get(
        f"{DOCUMENTS_ENDPOINT}/00000000-0000-0000-0000-000000000000/classification"
    )

    assert response.status_code == 404


def test_post_ocr_required_document_returns_409(client: TestClient) -> None:
    created = _create_document(client, ["", ""], "scan.pdf")
    assert created["status"] == "ocr_required"

    response = client.post(f"{DOCUMENTS_ENDPOINT}/{created['id']}/classification")

    assert response.status_code == 409


def test_post_with_unconfigured_provider_returns_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    created = _create_document(client, ["Some plain body text."], "doc.pdf")

    def _raise_unavailable(settings: object) -> object:
        raise ProviderUnavailableError("not configured")

    monkeypatch.setattr(
        "app.services.classification._build_provider", _raise_unavailable
    )

    response = client.post(f"{DOCUMENTS_ENDPOINT}/{created['id']}/classification")

    assert response.status_code == 503


def test_low_confidence_result_routes_to_generic_and_persists(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    page_text = "Some ambiguous document text that is hard to classify."
    created = _create_document(client, [page_text], "ambiguous.pdf")
    candidate = ClassificationCandidate.model_validate(
        {
            "document_type": "contract",
            "confidence": 0.2,
            "reason": "weak signal",
            "evidence": [{"page": 1, "text": page_text}],
        }
    )
    provider = _FakeProvider(candidate)
    monkeypatch.setattr(
        "app.services.classification._build_provider", lambda settings: provider
    )

    response = client.post(f"{DOCUMENTS_ENDPOINT}/{created['id']}/classification")

    assert response.status_code == 201
    assert response.json()["document_type"] == "generic"


def test_malformed_uuid_returns_422(client: TestClient) -> None:
    response = client.post(f"{DOCUMENTS_ENDPOINT}/not-a-uuid/classification")

    assert response.status_code == 422
