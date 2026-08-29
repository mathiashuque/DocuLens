"""API integration tests for POST/GET /api/documents/{id}/analysis.

Both the classification and analysis provider boundaries are monkeypatched
to fake in-process implementations; no test in this module makes a network
call or requires credentials.
"""

from collections.abc import Iterator
from typing import Any

import pymupdf
import pytest
from app.main import app
from fastapi.testclient import TestClient

from agent.analysis.provider import ProviderMetadata as AnalysisProviderMetadata
from agent.analysis.provider import (
    ProviderUnavailableError as AnalysisProviderUnavailableError,
)
from agent.analysis.types import (
    DocumentSummaryCandidate,
    FindingCandidate,
    GenericAnalysisCandidate,
)
from agent.classification.provider import (
    ProviderMetadata as ClassificationProviderMetadata,
)
from agent.classification.types import ClassificationCandidate
from agent.extractors.contract.provider import (
    ProviderMetadata as ContractProviderMetadata,
)
from agent.extractors.contract.types import (
    ContractExtractionCandidate,
    PartyCandidate,
)

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


class _FakeClassificationProvider:
    def __init__(self, page_text: str) -> None:
        self._page_text = page_text
        self.calls = 0

    async def classify(self, *, system_instruction: str, user_content: str):
        self.calls += 1
        candidate = ClassificationCandidate.model_validate(
            {
                "document_type": "generic",
                "confidence": 0.9,
                "reason": "Reads like a generic document.",
                "evidence": [{"page": 1, "text": self._page_text}],
            }
        )
        return candidate, ClassificationProviderMetadata(
            provider="openai", model="classify-test"
        )


class _FakeAnalysisProvider:
    def __init__(self, page_text: str) -> None:
        self._page_text = page_text
        self.extract_calls = 0
        self.repair_calls = 0

    async def extract(self, *, system_instruction: str, user_content: str):
        self.extract_calls += 1
        candidate = GenericAnalysisCandidate(
            summary=DocumentSummaryCandidate(
                title="Summary", purpose="Explains the document.", summary="A summary."
            ),
            findings=[
                FindingCandidate(
                    title="Key point",
                    description="An important point.",
                    category="general",
                    importance="medium",
                    source_page=1,
                    evidence=self._page_text,
                    confidence=0.8,
                )
            ],
            important_dates=[],
            risks=[],
        )
        return candidate, AnalysisProviderMetadata(
            provider="openai", model="analysis-test"
        )

    async def repair(self, *, system_instruction: str, user_content: str):
        self.repair_calls += 1
        raise AssertionError("repair should not be called on a valid candidate")


def _patch_providers(monkeypatch: pytest.MonkeyPatch, page_text: str):
    classification_provider = _FakeClassificationProvider(page_text)
    analysis_provider = _FakeAnalysisProvider(page_text)
    monkeypatch.setattr(
        "app.services.classification._build_provider",
        lambda settings: classification_provider,
    )
    monkeypatch.setattr(
        "app.services.analysis._build_provider", lambda settings: analysis_provider
    )
    return classification_provider, analysis_provider


class _FakeContractClassificationProvider:
    def __init__(self, page_text: str) -> None:
        self._page_text = page_text
        self.calls = 0

    async def classify(self, *, system_instruction: str, user_content: str):
        self.calls += 1
        candidate = ClassificationCandidate.model_validate(
            {
                "document_type": "contract",
                "confidence": 0.95,
                "reason": "Reads like a services agreement.",
                "evidence": [{"page": 1, "text": self._page_text}],
            }
        )
        return candidate, ClassificationProviderMetadata(
            provider="openai", model="classify-test"
        )


class _FakeContractProvider:
    def __init__(self, page_text: str) -> None:
        self._page_text = page_text
        self.extract_calls = 0
        self.repair_calls = 0

    async def extract(self, *, system_instruction: str, user_content: str):
        self.extract_calls += 1
        candidate = ContractExtractionCandidate(
            parties=[
                PartyCandidate(
                    name="Northstar Hosting Ltd.",
                    role="provider",
                    source_page=1,
                    evidence=self._page_text,
                    confidence=0.9,
                )
            ]
        )
        return candidate, ContractProviderMetadata(
            provider="openai", model="contract-test"
        )

    async def repair(self, *, system_instruction: str, user_content: str):
        self.repair_calls += 1
        raise AssertionError("repair should not be called on a valid candidate")


def _patch_contract_providers(monkeypatch: pytest.MonkeyPatch, page_text: str):
    classification_provider = _FakeContractClassificationProvider(page_text)
    analysis_provider = _FakeAnalysisProvider(page_text)
    contract_provider = _FakeContractProvider(page_text)
    monkeypatch.setattr(
        "app.services.classification._build_provider",
        lambda settings: classification_provider,
    )
    monkeypatch.setattr(
        "app.services.analysis._build_provider", lambda settings: analysis_provider
    )
    monkeypatch.setattr(
        "app.services.analysis._build_contract_provider",
        lambda settings: contract_provider,
    )
    return classification_provider, analysis_provider, contract_provider


def test_post_returns_201_with_typed_shape(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    page_text = "This is a generic memo about quarterly planning."
    created = _create_document(client, [page_text], "memo.pdf")
    _patch_providers(monkeypatch, page_text)

    response = client.post(f"{DOCUMENTS_ENDPOINT}/{created['id']}/analysis")

    assert response.status_code == 201
    body = response.json()
    assert body["document_id"] == created["id"]
    assert body["document_type"] == "generic"
    assert body["extractor"] == "generic"
    assert body["status"] == "completed"
    assert body["summary"]["purpose"] == "Explains the document."
    assert body["findings"][0]["source_page"] == 1
    assert body["findings"][0]["evidence"] == page_text
    assert body["important_dates"] == []
    assert body["risks"] == []
    assert body["provider"] == "openai"


def test_repeated_post_reuses_result_without_second_provider_calls(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    page_text = "This is a generic memo about quarterly planning."
    created = _create_document(client, [page_text], "memo.pdf")
    classification_provider, analysis_provider = _patch_providers(
        monkeypatch, page_text
    )

    first = client.post(f"{DOCUMENTS_ENDPOINT}/{created['id']}/analysis")
    second = client.post(f"{DOCUMENTS_ENDPOINT}/{created['id']}/analysis")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert classification_provider.calls == 1
    assert analysis_provider.extract_calls == 1


def test_get_returns_latest_completed_without_invoking_provider(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    page_text = "This is a generic memo about quarterly planning."
    created = _create_document(client, [page_text], "memo.pdf")
    _patch_providers(monkeypatch, page_text)
    client.post(f"{DOCUMENTS_ENDPOINT}/{created['id']}/analysis")

    def _fail(settings: object) -> object:
        raise AssertionError("GET must never invoke a provider")

    monkeypatch.setattr("app.services.analysis._build_provider", _fail)
    monkeypatch.setattr("app.services.classification._build_provider", _fail)

    response = client.get(f"{DOCUMENTS_ENDPOINT}/{created['id']}/analysis")

    assert response.status_code == 200
    assert response.json()["document_type"] == "generic"


def test_get_returns_404_when_no_completed_analysis_exists(client: TestClient) -> None:
    created = _create_document(client, ["Some plain body text."], "doc.pdf")

    response = client.get(f"{DOCUMENTS_ENDPOINT}/{created['id']}/analysis")

    assert response.status_code == 404


def test_post_unknown_document_returns_404(client: TestClient) -> None:
    response = client.post(
        f"{DOCUMENTS_ENDPOINT}/00000000-0000-0000-0000-000000000000/analysis"
    )

    assert response.status_code == 404


def test_get_unknown_document_returns_404(client: TestClient) -> None:
    response = client.get(
        f"{DOCUMENTS_ENDPOINT}/00000000-0000-0000-0000-000000000000/analysis"
    )

    assert response.status_code == 404


def test_post_ocr_required_document_returns_409(client: TestClient) -> None:
    created = _create_document(client, ["", ""], "scan.pdf")
    assert created["status"] == "ocr_required"

    response = client.post(f"{DOCUMENTS_ENDPOINT}/{created['id']}/analysis")

    assert response.status_code == 409


def test_post_with_unconfigured_analysis_provider_returns_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    page_text = "Some plain body text."
    created = _create_document(client, [page_text], "doc.pdf")
    monkeypatch.setattr(
        "app.services.classification._build_provider",
        lambda settings: _FakeClassificationProvider(page_text),
    )

    def _raise_unavailable(settings: object) -> object:
        raise AnalysisProviderUnavailableError("not configured")

    monkeypatch.setattr("app.services.analysis._build_provider", _raise_unavailable)

    response = client.post(f"{DOCUMENTS_ENDPOINT}/{created['id']}/analysis")

    assert response.status_code == 503


def test_contract_document_returns_specialized_analysis(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    page_text = "Northstar Hosting Ltd. (Provider) enters this Services Agreement."
    created = _create_document(client, [page_text], "agreement.pdf")
    classification_provider, analysis_provider, contract_provider = (
        _patch_contract_providers(monkeypatch, page_text)
    )

    response = client.post(f"{DOCUMENTS_ENDPOINT}/{created['id']}/analysis")

    assert response.status_code == 201
    body = response.json()
    assert body["document_type"] == "contract"
    assert body["extractor"] == "contract_terms"
    assert body["specialized_analysis"]["type"] == "contract"
    assert (
        body["specialized_analysis"]["parties"][0]["name"] == "Northstar Hosting Ltd."
    )
    assert body["specialized_analysis"]["obligations"] == []
    assert classification_provider.calls == 1
    assert analysis_provider.extract_calls == 1
    assert contract_provider.extract_calls == 1


def test_generic_document_has_no_specialized_analysis_and_no_contract_call(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    page_text = "This is a generic memo about quarterly planning."
    created = _create_document(client, [page_text], "memo.pdf")
    _patch_providers(monkeypatch, page_text)

    def _fail(settings: object) -> object:
        raise AssertionError("generic route must never build a contract provider")

    monkeypatch.setattr("app.services.analysis._build_contract_provider", _fail)

    response = client.post(f"{DOCUMENTS_ENDPOINT}/{created['id']}/analysis")

    assert response.status_code == 201
    body = response.json()
    assert body["extractor"] == "generic"
    assert body["specialized_analysis"] is None


def test_malformed_uuid_returns_422(client: TestClient) -> None:
    response = client.post(f"{DOCUMENTS_ENDPOINT}/not-a-uuid/analysis")

    assert response.status_code == 422
