from collections.abc import Iterator

import pytest
from app.db.session import dispose_engine
from app.demo.seed import seed_demos
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def seeded_client(
    postgres_url: str, clean_tables: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    import asyncio

    asyncio.run(dispose_engine())
    asyncio.run(seed_demos())
    asyncio.run(dispose_engine())
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_demo_list_is_exactly_three_safe_cards(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/demos")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    assert {item["slug"] for item in body} == {
        "sample-contract",
        "sample-technical-specification",
        "sample-generic-report",
    }
    assert all("pages" not in item and "evidence" not in item for item in body)


def test_demo_detail_reuses_document_contract_and_unknown_is_404(
    seeded_client: TestClient,
) -> None:
    response = seeded_client.get("/api/demos/sample-contract")
    assert response.status_code == 200
    body = response.json()
    assert body["demo_slug"] == "sample-contract"
    assert len(body["pages"]) == 3
    assert len(body["demo_questions"]) == 3
    assert seeded_client.get("/api/demos/not-a-demo").status_code == 404
