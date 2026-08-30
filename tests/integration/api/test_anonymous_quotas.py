import uuid
from collections.abc import Iterator

import pymupdf
import pytest
from app.core.anonymous_session import issue_token
from app.main import app
from fastapi.testclient import TestClient

from retrieval.embedding import EmbeddingProviderRequestError

SECRET = "integration-public-secret-at-least-thirty-two-bytes"


def _pdf(text: str) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


@pytest.fixture
def public_client(
    postgres_url: str, clean_tables: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv("ANONYMOUS_SESSION_SECRET", SECRET)
    monkeypatch.setenv("MAX_INDEXES_PER_DAY", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "not-real")
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _create(client: TestClient, name: str) -> str:
    response = client.post(
        "/api/documents",
        files={"file": (name, _pdf("Synthetic document text."), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _headers() -> dict[str, str]:
    return {"x-doculens-anonymous-session": issue_token(SECRET)}


def test_chargeable_endpoint_requires_valid_session_but_demo_read_is_free(
    public_client: TestClient,
) -> None:
    document_id = uuid.uuid4()
    chargeable_requests = (
        (f"/api/documents/{document_id}/classification", None),
        (f"/api/documents/{document_id}/index", None),
        (f"/api/documents/{document_id}/search", {"query": "bounded"}),
        (f"/api/documents/{document_id}/questions", {"question": "bounded"}),
    )
    for path, body in chargeable_requests:
        assert public_client.post(path, json=body).status_code == 401
    assert public_client.get("/api/demos").status_code == 200


def test_provider_attempt_consumes_once_and_next_request_gets_typed_429(
    public_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _create(public_client, "one.pdf")
    second = _create(public_client, "two.pdf")

    class FailingProvider:
        async def embed_documents(self, texts: list[str]) -> None:
            raise EmbeddingProviderRequestError("synthetic failure")

    monkeypatch.setattr(
        "app.services.indexing._build_provider",
        lambda settings: FailingProvider(),
    )
    headers = _headers()
    assert (
        public_client.post(f"/api/documents/{first}/index", headers=headers).status_code
        == 502
    )
    usage = public_client.get("/api/usage", headers=headers)
    assert usage.status_code == 200
    index_allowance = next(
        item for item in usage.json()["allowances"] if item["category"] == "index"
    )
    assert index_allowance["remaining"] == 0
    response = public_client.post(f"/api/documents/{second}/index", headers=headers)
    assert response.status_code == 429
    assert response.json() == {
        "error": "quota_exceeded",
        "category": "index",
        "limit": 1,
        "remaining": 0,
        "retry_at": response.json()["retry_at"],
    }
    assert response.json()["retry_at"].endswith("Z")
    assert int(response.headers["retry-after"]) >= 0


def test_weak_secret_fails_closed_without_breaking_free_reads(
    public_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ANONYMOUS_SESSION_SECRET", "too-short")
    assert public_client.get("/health").status_code == 200
    assert public_client.get("/api/demos").status_code == 200
    document_id = _create(public_client, "weak-secret.pdf")
    response = public_client.post(
        f"/api/documents/{document_id}/index", headers=_headers()
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Usage protection is not configured."}
