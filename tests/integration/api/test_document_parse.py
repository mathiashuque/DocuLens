"""API integration tests for POST /api/documents/parse."""

from collections.abc import Iterator

import pymupdf
import pytest
from app.core.config import UploadSettings, load_upload_settings
from app.main import app
from fastapi.testclient import TestClient

ENDPOINT = "/api/documents/parse"


def _build_pdf(pages_text: list[str]) -> bytes:
    document = pymupdf.open()
    for text in pages_text:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_successful_upload_returns_typed_shape(client: TestClient) -> None:
    data = _build_pdf(["First page text", "Second page text"])

    response = client.post(
        ENDPOINT,
        files={"file": ("example.pdf", data, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "example.pdf"
    assert body["status"] == "parsed"
    assert body["page_count"] == 2
    assert [page["page_number"] for page in body["pages"]] == [1, 2]
    assert "First page text" in body["pages"][0]["text"]
    assert "Second page text" in body["pages"][1]["text"]


def test_missing_file_is_rejected(client: TestClient) -> None:
    response = client.post(ENDPOINT)

    assert response.status_code == 422


def test_wrong_declared_mime_type_is_rejected(client: TestClient) -> None:
    data = _build_pdf(["text"])

    response = client.post(
        ENDPOINT,
        files={"file": ("example.pdf", data, "text/plain")},
    )

    assert response.status_code == 415


def test_pdf_mime_with_wrong_signature_is_rejected(client: TestClient) -> None:
    response = client.post(
        ENDPOINT,
        files={"file": ("example.pdf", b"not a real pdf", "application/pdf")},
    )

    assert response.status_code == 415


def test_malformed_pdf_is_rejected(client: TestClient) -> None:
    response = client.post(
        ENDPOINT,
        files={
            "file": (
                "example.pdf",
                b"%PDF-1.4\nnot really valid content",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 422


def test_upload_size_limit_is_enforced(client: TestClient) -> None:
    app.dependency_overrides[load_upload_settings] = lambda: UploadSettings(
        max_upload_mb=1, max_document_pages=40
    )

    oversized = b"%PDF-" + (b"0" * (2 * 1024 * 1024))
    response = client.post(
        ENDPOINT,
        files={"file": ("example.pdf", oversized, "application/pdf")},
    )

    assert response.status_code == 413


def test_page_count_limit_is_enforced(client: TestClient) -> None:
    app.dependency_overrides[load_upload_settings] = lambda: UploadSettings(
        max_upload_mb=10, max_document_pages=1
    )

    data = _build_pdf(["one", "two"])
    response = client.post(
        ENDPOINT,
        files={"file": ("example.pdf", data, "application/pdf")},
    )

    assert response.status_code == 413


# Missing-filename fallback is covered in tests/unit/services/test_document_parsing.py;
# HTTP multipart cannot express a file part with no filename through the test client.
def test_filename_is_sanitized(client: TestClient) -> None:
    data = _build_pdf(["text"])

    response = client.post(
        ENDPOINT,
        files={"file": ("../../etc/passwd.pdf", data, "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["filename"] == "passwd.pdf"


def test_no_text_pdf_returns_ocr_required(client: TestClient) -> None:
    data = _build_pdf(["", ""])

    response = client.post(
        ENDPOINT,
        files={"file": ("scan.pdf", data, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ocr_required"
    assert body["page_count"] == 2
