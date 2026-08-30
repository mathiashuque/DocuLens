"""Deterministic citation/evidence validation against retrieved context and
original persisted page text."""

import uuid

from agent.grounded_qa.types import CitationCandidate, GroundedAnswerCandidate
from retrieval.citation_validation import validate_candidate
from retrieval.grounded_qa import EvidenceContextItem

DOC_PAGES = {
    1: "The agreement renews automatically for successive twelve month periods.",
    2: "Either party may terminate this agreement with sixty days written notice.",
}


def _chunk(
    chunk_id: uuid.UUID, text: str, page_start: int, page_end: int | None = None
):
    return EvidenceContextItem(
        chunk_id=chunk_id,
        chunk_index=0,
        text=text,
        page_start=page_start,
        page_end=page_end if page_end is not None else page_start,
        section_title=None,
        section_path=[],
    )


def test_insufficient_evidence_with_no_citations_is_valid() -> None:
    candidate = GroundedAnswerCandidate(
        status="insufficient_evidence", answer="not enough evidence", citations=[]
    )
    result = validate_candidate(candidate, context_items=[], document_pages={})
    assert result.valid
    assert result.citations == ()


def test_insufficient_evidence_with_citations_is_rejected() -> None:
    candidate = GroundedAnswerCandidate(
        status="insufficient_evidence",
        answer="no evidence",
        citations=[CitationCandidate(chunk_id="c1", page=1, evidence="x")],
    )
    result = validate_candidate(candidate, context_items=[], document_pages={})
    assert not result.valid


def test_answered_requires_at_least_one_citation() -> None:
    candidate = GroundedAnswerCandidate(status="answered", answer="Yes.", citations=[])
    result = validate_candidate(candidate, context_items=[], document_pages=DOC_PAGES)
    assert not result.valid


def test_valid_single_citation_passes() -> None:
    chunk_id = uuid.uuid4()
    context = [_chunk(chunk_id, DOC_PAGES[1], page_start=1)]
    candidate = GroundedAnswerCandidate(
        status="answered",
        answer="Yes, it renews automatically.",
        citations=[
            CitationCandidate(
                chunk_id=str(chunk_id),
                page=1,
                evidence="renews automatically for successive twelve month periods",
            )
        ],
    )
    result = validate_candidate(
        candidate, context_items=context, document_pages=DOC_PAGES
    )
    assert result.valid
    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == chunk_id
    assert result.citations[0].page == 1


def test_valid_multi_citation_passes() -> None:
    chunk_a = uuid.uuid4()
    chunk_b = uuid.uuid4()
    context = [
        _chunk(chunk_a, DOC_PAGES[1], page_start=1),
        _chunk(chunk_b, DOC_PAGES[2], page_start=2),
    ]
    candidate = GroundedAnswerCandidate(
        status="answered",
        answer="It renews automatically but either party may terminate with notice.",
        citations=[
            CitationCandidate(
                chunk_id=str(chunk_a), page=1, evidence="renews automatically"
            ),
            CitationCandidate(
                chunk_id=str(chunk_b),
                page=2,
                evidence="terminate this agreement with sixty days written notice",
            ),
        ],
    )
    result = validate_candidate(
        candidate, context_items=context, document_pages=DOC_PAGES
    )
    assert result.valid
    assert len(result.citations) == 2


def test_unknown_chunk_id_is_rejected() -> None:
    context = [_chunk(uuid.uuid4(), DOC_PAGES[1], page_start=1)]
    candidate = GroundedAnswerCandidate(
        status="answered",
        answer="Yes.",
        citations=[
            CitationCandidate(
                chunk_id=str(uuid.uuid4()), page=1, evidence="renews automatically"
            )
        ],
    )
    result = validate_candidate(
        candidate, context_items=context, document_pages=DOC_PAGES
    )
    assert not result.valid
    assert "not in the retrieved context" in result.errors[0]


def test_cross_document_chunk_reference_is_rejected() -> None:
    # A chunk_id from a different document's context would simply never be
    # present in this request's own `context_items`, so it fails the same
    # "not in retrieved context" path — proving cross-document references
    # cannot pass.
    other_chunk_id = uuid.uuid4()
    context = [_chunk(uuid.uuid4(), DOC_PAGES[1], page_start=1)]
    candidate = GroundedAnswerCandidate(
        status="answered",
        answer="Yes.",
        citations=[
            CitationCandidate(
                chunk_id=str(other_chunk_id), page=1, evidence="renews automatically"
            )
        ],
    )
    result = validate_candidate(
        candidate, context_items=context, document_pages=DOC_PAGES
    )
    assert not result.valid


def test_invalid_page_out_of_chunk_range_is_rejected() -> None:
    chunk_id = uuid.uuid4()
    context = [_chunk(chunk_id, DOC_PAGES[1], page_start=1, page_end=1)]
    candidate = GroundedAnswerCandidate(
        status="answered",
        answer="Yes.",
        citations=[
            CitationCandidate(
                chunk_id=str(chunk_id), page=2, evidence="renews automatically"
            )
        ],
    )
    result = validate_candidate(
        candidate, context_items=context, document_pages=DOC_PAGES
    )
    assert not result.valid
    assert "outside chunk" in result.errors[0]


def test_empty_evidence_is_rejected() -> None:
    chunk_id = uuid.uuid4()
    context = [_chunk(chunk_id, DOC_PAGES[1], page_start=1)]
    candidate = GroundedAnswerCandidate(
        status="answered",
        answer="Yes.",
        citations=[CitationCandidate(chunk_id=str(chunk_id), page=1, evidence="   ")],
    )
    result = validate_candidate(
        candidate, context_items=context, document_pages=DOC_PAGES
    )
    assert not result.valid


def test_evidence_absent_from_context_text_is_rejected() -> None:
    chunk_id = uuid.uuid4()
    context = [_chunk(chunk_id, DOC_PAGES[1], page_start=1)]
    candidate = GroundedAnswerCandidate(
        status="answered",
        answer="Yes.",
        citations=[
            CitationCandidate(
                chunk_id=str(chunk_id),
                page=1,
                evidence="this text was never in the chunk",
            )
        ],
    )
    result = validate_candidate(
        candidate, context_items=context, document_pages=DOC_PAGES
    )
    assert not result.valid
    assert "not present in the context" in result.errors[0]


def test_evidence_present_in_chunk_but_absent_from_claimed_page_is_rejected() -> None:
    """A chunk spanning two pages whose text happens to also contain a
    substring matching page 2's wording, cited against page 1, must fail:
    the honest page resolution is checked against the *claimed* page's own
    original text, never guessed from the chunk's range."""
    chunk_id = uuid.uuid4()
    spanning_text = DOC_PAGES[1] + " " + DOC_PAGES[2]
    context = [_chunk(chunk_id, spanning_text, page_start=1, page_end=2)]
    candidate = GroundedAnswerCandidate(
        status="answered",
        answer="Either party may terminate with notice.",
        citations=[
            CitationCandidate(
                chunk_id=str(chunk_id),
                page=1,
                evidence="terminate this agreement with sixty days written notice",
            )
        ],
    )
    result = validate_candidate(
        candidate, context_items=context, document_pages=DOC_PAGES
    )
    assert not result.valid
    assert "does not appear on page 1" in result.errors[0]


def test_honest_page_resolution_accepts_correct_page_for_spanning_chunk() -> None:
    chunk_id = uuid.uuid4()
    spanning_text = DOC_PAGES[1] + " " + DOC_PAGES[2]
    context = [_chunk(chunk_id, spanning_text, page_start=1, page_end=2)]
    candidate = GroundedAnswerCandidate(
        status="answered",
        answer="Either party may terminate with notice.",
        citations=[
            CitationCandidate(
                chunk_id=str(chunk_id),
                page=2,
                evidence="terminate this agreement with sixty days written notice",
            )
        ],
    )
    result = validate_candidate(
        candidate, context_items=context, document_pages=DOC_PAGES
    )
    assert result.valid
    assert result.citations[0].page == 2


def test_nonexistent_page_is_rejected() -> None:
    chunk_id = uuid.uuid4()
    context = [_chunk(chunk_id, DOC_PAGES[1], page_start=1, page_end=99)]
    candidate = GroundedAnswerCandidate(
        status="answered",
        answer="Yes.",
        citations=[
            CitationCandidate(
                chunk_id=str(chunk_id), page=99, evidence="renews automatically"
            )
        ],
    )
    result = validate_candidate(
        candidate, context_items=context, document_pages=DOC_PAGES
    )
    assert not result.valid
    assert "does not exist" in result.errors[0]


def test_duplicate_citations_are_normalized_without_losing_distinct_evidence() -> None:
    chunk_id = uuid.uuid4()
    context = [_chunk(chunk_id, DOC_PAGES[1], page_start=1)]
    candidate = GroundedAnswerCandidate(
        status="answered",
        answer="It renews automatically.",
        citations=[
            CitationCandidate(
                chunk_id=str(chunk_id), page=1, evidence="renews automatically"
            ),
            CitationCandidate(
                chunk_id=str(chunk_id), page=1, evidence="renews   automatically"
            ),
            CitationCandidate(
                chunk_id=str(chunk_id),
                page=1,
                evidence="successive twelve month periods",
            ),
        ],
    )
    result = validate_candidate(
        candidate, context_items=context, document_pages=DOC_PAGES
    )
    assert result.valid
    assert len(result.citations) == 2
