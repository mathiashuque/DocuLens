"""API integration tests for POST /api/documents/{id}/questions.

The embedding provider boundary is monkeypatched to the deterministic fake
adapter and the generation provider boundary to a deterministic stub; no
test in this module makes a network call or requires credentials.
"""

import uuid
from collections.abc import Iterator

import pymupdf
import pytest
from app.main import app
from fastapi.testclient import TestClient

from agent.grounded_qa.provider import ProviderMetadata
from agent.grounded_qa.types import CitationCandidate, GroundedAnswerCandidate
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


class _StubGroundedQaProvider:
    """Deterministic stand-in that always cites the first retrieved chunk's
    text verbatim, or returns insufficient_evidence when told to."""

    def __init__(self, *, insufficient: bool = False) -> None:
        self.insufficient = insufficient

    async def answer(self, *, system_instruction: str, user_content: str):
        if self.insufficient:
            candidate = GroundedAnswerCandidate(
                status="insufficient_evidence",
                answer="not enough evidence",
                citations=[],
            )
        else:
            chunk_id, page, evidence = self._first_block(user_content)
            candidate = GroundedAnswerCandidate(
                status="answered",
                answer="Yes, per the cited evidence.",
                citations=[
                    CitationCandidate(chunk_id=chunk_id, page=page, evidence=evidence)
                ],
            )
        return candidate, ProviderMetadata(provider="fake", model="fake")

    async def repair(self, *, system_instruction: str, user_content: str):
        return await self.answer(
            system_instruction=system_instruction, user_content=user_content
        )

    @staticmethod
    def _first_block(user_content: str) -> tuple[str, int, str]:
        import re

        match = re.search(
            r'<block chunk_id="([^"]+)" page_start="(\d+)" page_end="(\d+)">\n(.*?)\n</block>',
            user_content,
            re.DOTALL,
        )
        assert match is not None
        chunk_id, page_start, _page_end, text = match.groups()
        return chunk_id, int(page_start), text.strip()


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
    monkeypatch.setattr(
        "app.services.grounded_qa._build_provider",
        lambda settings: _StubGroundedQaProvider(),
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


def test_questions_unknown_document_returns_404(client: TestClient) -> None:
    response = client.post(
        f"{DOCUMENTS_ENDPOINT}/{uuid.uuid4()}/questions", json={"question": "hello?"}
    )
    assert response.status_code == 404


def test_questions_without_index_returns_404(client: TestClient) -> None:
    data = _build_pdf(["Some page text."])
    created = client.post(
        DOCUMENTS_ENDPOINT, files={"file": ("no_index.pdf", data, "application/pdf")}
    )
    document = created.json()

    response = client.post(
        f"{DOCUMENTS_ENDPOINT}/{document['id']}/questions", json={"question": "hello?"}
    )
    assert response.status_code == 404


def test_questions_blank_question_returns_422(client: TestClient) -> None:
    document = _create_and_index(client, ["Some content."], "blank.pdf")
    response = client.post(
        f"{DOCUMENTS_ENDPOINT}/{document['id']}/questions", json={"question": "   "}
    )
    assert response.status_code == 422


def test_questions_top_k_out_of_bounds_returns_422(client: TestClient) -> None:
    document = _create_and_index(client, ["Some content."], "topk.pdf")
    response = client.post(
        f"{DOCUMENTS_ENDPOINT}/{document['id']}/questions",
        json={"question": "hello?", "top_k": 0},
    )
    assert response.status_code == 422


def test_questions_answered_returns_valid_citation(client: TestClient) -> None:
    document = _create_and_index(
        client,
        ["Either party may terminate this agreement with sixty days written notice."],
        "contract.pdf",
    )

    response = client.post(
        f"{DOCUMENTS_ENDPOINT}/{document['id']}/questions",
        json={"question": "Can either party terminate the agreement?", "top_k": 3},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["document_id"] == document["id"]
    assert len(body["citations"]) == 1
    assert body["citations"][0]["page"] == 1
    assert "vector" not in body and "prompt" not in body


def test_questions_insufficient_evidence_shape(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.services.grounded_qa._build_provider",
        lambda settings: _StubGroundedQaProvider(insufficient=True),
    )
    document = _create_and_index(
        client, ["Unrelated content about widgets."], "widgets.pdf"
    )

    response = client.post(
        f"{DOCUMENTS_ENDPOINT}/{document['id']}/questions",
        json={"question": "Who approved the final budget?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "insufficient_evidence"
    assert body["citations"] == []
    assert body["answer"] == (
        "The document does not contain enough evidence to answer this question."
    )
