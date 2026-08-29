"""Integration test for the liveness endpoint."""

from app.main import app
from fastapi.testclient import TestClient


def test_health_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}
