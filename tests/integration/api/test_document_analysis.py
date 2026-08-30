"""The predefined-analysis endpoint is retired: both methods on
`/api/documents/{document_id}/analysis` must be unregistered routes, not
compatibility responses that still invoke analysis.
"""

import uuid
from collections.abc import Iterator

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client(
    postgres_url: str, clean_tables: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_post_analysis_is_unregistered(client: TestClient) -> None:
    document_id = uuid.uuid4()
    response = client.post(f"/api/documents/{document_id}/analysis")
    assert response.status_code == 404


def test_get_analysis_is_unregistered(client: TestClient) -> None:
    document_id = uuid.uuid4()
    response = client.get(f"/api/documents/{document_id}/analysis")
    assert response.status_code == 404


def test_analysis_path_absent_from_openapi_schema(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert not any("analysis" in path for path in schema["paths"])
