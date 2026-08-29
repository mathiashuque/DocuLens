"""Deterministic bounded context construction for grounded QA."""

import uuid
from dataclasses import dataclass

from retrieval.grounded_qa import build_context


@dataclass
class _Result:
    chunk_id: uuid.UUID
    chunk_index: int
    text: str
    page_start: int
    page_end: int
    section_title: str | None
    section_path: list[str]
    score: float


def _result(index: int, text: str) -> _Result:
    return _Result(
        chunk_id=uuid.uuid4(),
        chunk_index=index,
        text=text,
        page_start=index + 1,
        page_end=index + 1,
        section_title=None,
        section_path=[],
        score=1.0 - index * 0.1,
    )


def test_preserves_retrieval_order_and_identity() -> None:
    results = [_result(0, "first"), _result(1, "second")]
    items = build_context(results, max_chunks=5, max_chars=1000)
    assert [item.chunk_id for item in items] == [r.chunk_id for r in results]
    assert items[0].text == "first"
    assert items[1].text == "second"


def test_stops_at_max_chunks() -> None:
    results = [_result(i, f"chunk {i}") for i in range(10)]
    items = build_context(results, max_chunks=3, max_chars=10000)
    assert len(items) == 3


def test_excludes_whole_chunk_that_would_exceed_char_budget() -> None:
    results = [_result(0, "x" * 50), _result(1, "y" * 50), _result(2, "short")]
    items = build_context(results, max_chunks=5, max_chars=60)
    # First chunk (50 chars) fits; second (another 50) would exceed the
    # budget and is skipped whole (never truncated); third (short) still fits.
    assert [item.text for item in items] == ["x" * 50, "short"]


def test_empty_results_yield_empty_context() -> None:
    assert build_context([], max_chunks=5, max_chars=1000) == []


def test_zero_budget_yields_empty_context() -> None:
    results = [_result(0, "text")]
    assert build_context(results, max_chunks=0, max_chars=1000) == []
    assert build_context(results, max_chunks=5, max_chars=0) == []
