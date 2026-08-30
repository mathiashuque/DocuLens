"""Discriminated answered/insufficient-evidence schema serialization."""

import uuid

from app.schemas.grounded_qa import (
    AnsweredResponse,
    CitationResponse,
    InsufficientEvidenceResponse,
)


def test_answered_response_serializes_with_status_and_citations() -> None:
    document_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    response = AnsweredResponse(
        document_id=document_id,
        question="Does it renew?",
        answer="Yes, automatically.",
        citations=[
            CitationResponse(chunk_id=chunk_id, page=1, evidence="renews automatically")
        ],
    )
    data = response.model_dump(mode="json")
    assert data["status"] == "answered"
    assert data["citations"][0]["chunk_id"] == str(chunk_id)


def test_insufficient_evidence_response_has_empty_citations_by_default() -> None:
    response = InsufficientEvidenceResponse(
        document_id=uuid.uuid4(),
        question="Who approved this?",
        answer="The document does not contain enough evidence to answer this question.",
    )
    data = response.model_dump(mode="json")
    assert data["status"] == "insufficient_evidence"
    assert data["citations"] == []
