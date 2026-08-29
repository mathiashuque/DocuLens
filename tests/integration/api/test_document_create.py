"""API integration tests for POST/GET /api/documents (persisted documents)."""

import hashlib
from collections.abc import Iterator

import pymupdf
import pytest
from app.db.session import get_session
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

ENDPOINT = "/api/documents"


def _build_pdf(pages_text: list[str]) -> bytes:
    document = pymupdf.open()
    for text_content in pages_text:
        page = document.new_page()
        if text_content:
            page.insert_text((72, 72), text_content)
    data = document.tobytes()
    document.close()
    return data


async def _document_count(postgres_url: str) -> int:
    engine = create_async_engine(postgres_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT count(*) FROM documents"))
            return result.scalar_one()
    finally:
        await engine.dispose()


@pytest.fixture
def client(
    postgres_url: str, clean_tables: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_returns_201_with_typed_shape(client: TestClient) -> None:
    data = _build_pdf(["First page text", "Second page text"])

    response = client.post(
        ENDPOINT, files={"file": ("example.pdf", data, "application/pdf")}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "example.pdf"
    assert body["status"] == "parsed"
    assert body["page_count"] == 2
    assert body["content_hash"] == hashlib.sha256(data).hexdigest()
    assert [page["page_number"] for page in body["pages"]] == [1, 2]
    assert "First page text" in body["pages"][0]["text"]
    assert "id" in body
    assert "created_at" in body


def test_get_returns_identical_ordered_pages(client: TestClient) -> None:
    data = _build_pdf(["one", "two"])
    created = client.post(
        ENDPOINT, files={"file": ("doc.pdf", data, "application/pdf")}
    ).json()

    response = client.get(f"{ENDPOINT}/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_unknown_uuid_returns_404(client: TestClient) -> None:
    response = client.get(f"{ENDPOINT}/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found."}


def test_malformed_uuid_returns_validation_error(client: TestClient) -> None:
    response = client.get(f"{ENDPOINT}/not-a-uuid")

    assert response.status_code == 422


def test_blank_page_round_trips(client: TestClient) -> None:
    data = _build_pdf(["Some text", ""])

    response = client.post(
        ENDPOINT, files={"file": ("scan.pdf", data, "application/pdf")}
    )

    body = response.json()
    assert body["pages"][1]["page_number"] == 2
    assert body["pages"][1]["text"] == ""


def test_ocr_required_document_persists(client: TestClient) -> None:
    data = _build_pdf(["", ""])

    created = client.post(
        ENDPOINT, files={"file": ("scan.pdf", data, "application/pdf")}
    ).json()

    assert created["status"] == "ocr_required"
    fetched = client.get(f"{ENDPOINT}/{created['id']}").json()
    assert fetched["status"] == "ocr_required"


@pytest.mark.asyncio
async def test_malformed_pdf_creates_no_document(
    client: TestClient, postgres_url: str
) -> None:
    response = client.post(
        ENDPOINT,
        files={
            "file": (
                "bad.pdf",
                b"%PDF-1.4\nnot really valid content",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 422
    assert await _document_count(postgres_url) == 0


@pytest.mark.asyncio
async def test_unsupported_mime_creates_no_document(
    client: TestClient, postgres_url: str
) -> None:
    data = _build_pdf(["text"])

    response = client.post(
        ENDPOINT, files={"file": ("example.pdf", data, "text/plain")}
    )

    assert response.status_code == 415
    assert await _document_count(postgres_url) == 0


def test_duplicate_bytes_create_distinct_documents(client: TestClient) -> None:
    data = _build_pdf(["same content"])

    first = client.post(
        ENDPOINT, files={"file": ("a.pdf", data, "application/pdf")}
    ).json()
    second = client.post(
        ENDPOINT, files={"file": ("a.pdf", data, "application/pdf")}
    ).json()

    assert first["id"] != second["id"]
    expected_hash = hashlib.sha256(data).hexdigest()
    assert first["content_hash"] == second["content_hash"] == expected_hash


def test_parse_endpoint_unaffected_by_database_failure(client: TestClient) -> None:
    async def broken_session():  # type: ignore[no-untyped-def]
        raise ConnectionError("database is unreachable")
        yield  # pragma: no cover - generator must yield to satisfy the dependency type

    app.dependency_overrides[get_session] = broken_session
    data = _build_pdf(["text"])

    response = client.post(
        "/api/documents/parse",
        files={"file": ("example.pdf", data, "application/pdf")},
    )

    assert response.status_code == 200


def test_logs_do_not_contain_document_text_or_credentials(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("DEBUG")
    data = _build_pdf(["Extremely sensitive secret content"])

    client.post(ENDPOINT, files={"file": ("secret.pdf", data, "application/pdf")})

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "Extremely sensitive secret content" not in log_text
    assert "doculens_local_only" not in log_text
    assert "test_only_password" not in log_text
