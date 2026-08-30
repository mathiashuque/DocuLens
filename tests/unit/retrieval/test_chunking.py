import uuid

import pytest

from ingestion.models import DocumentPage
from retrieval.chunking import (
    ChunkingConfig,
    ChunkLimitExceededError,
    EmptyChunkOutputError,
    SectionInput,
    chunk_document,
)
from retrieval.tokenizer import estimate_tokens

DOC_ID = uuid.uuid4()


def _section(
    title: str,
    page_start: int,
    page_end: int,
    level: int = 1,
    path: list[str] | None = None,
) -> SectionInput:
    return SectionInput(
        id=uuid.uuid4(),
        title=title,
        page_start=page_start,
        page_end=page_end,
        section_path=path or [title],
        level=level,
    )


def test_single_short_section_produces_one_chunk_with_provenance() -> None:
    section = _section("Introduction", 1, 1)
    pages = [DocumentPage(page_number=1, text="Hello world this is short text.")]

    chunks = chunk_document(document_id=DOC_ID, pages=pages, sections=[section])

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.chunk_index == 0
    assert chunk.section_id == section.id
    assert chunk.section_title == "Introduction"
    assert chunk.section_path == ["Introduction"]
    assert chunk.page_start == 1
    assert chunk.page_end == 1
    assert chunk.document_id == DOC_ID
    assert chunk.token_estimate == estimate_tokens(chunk.text)


def test_page_aware_fallback_without_sections() -> None:
    pages = [
        DocumentPage(page_number=1, text="alpha beta gamma"),
        DocumentPage(page_number=2, text="delta epsilon zeta"),
    ]

    chunks = chunk_document(document_id=DOC_ID, pages=pages, sections=None)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.section_id is None
    assert chunk.section_title is None
    assert chunk.section_path == []
    assert chunk.page_start == 1
    assert chunk.page_end == 2
    assert "alpha" in chunk.text and "zeta" in chunk.text


def test_blank_pages_produce_no_empty_chunks_and_do_not_shift_page_numbers() -> None:
    pages = [
        DocumentPage(page_number=1, text="alpha beta"),
        DocumentPage(page_number=2, text="   "),
        DocumentPage(page_number=3, text="gamma delta"),
    ]

    chunks = chunk_document(document_id=DOC_ID, pages=pages, sections=None)

    all_text = " ".join(c.text for c in chunks)
    assert "alpha" in all_text and "gamma" in all_text
    pages_seen = {p for c in chunks for p in (c.page_start, c.page_end)}
    assert 2 not in pages_seen  # blank page never becomes a chunk's provenance


def test_unrelated_sections_are_never_merged() -> None:
    section_a = _section("Section A", 1, 1)
    section_b = _section("Section B", 2, 2)
    pages = [
        DocumentPage(page_number=1, text="short a"),
        DocumentPage(page_number=2, text="short b"),
    ]

    chunks = chunk_document(
        document_id=DOC_ID, pages=pages, sections=[section_a, section_b]
    )

    assert len(chunks) == 2
    assert chunks[0].section_id == section_a.id
    assert chunks[1].section_id == section_b.id
    assert chunks[0].page_end < chunks[1].page_start


def test_hierarchical_section_path_is_retained() -> None:
    parent = _section("5. Legal Terms", 1, 2, level=1, path=["5. Legal Terms"])
    child = _section(
        "5.3 Termination",
        1,
        1,
        level=2,
        path=["5. Legal Terms", "5.3 Termination"],
    )
    pages = [DocumentPage(page_number=1, text="termination clause text here")]

    chunks = chunk_document(document_id=DOC_ID, pages=pages, sections=[parent, child])

    assert len(chunks) == 1
    assert chunks[0].section_path == ["5. Legal Terms", "5.3 Termination"]
    assert chunks[0].section_id == child.id


def test_long_section_splits_into_overlapping_chunks_with_stable_order() -> None:
    words = [f"word{i}" for i in range(50)]
    section = _section("Long Section", 1, 1)
    pages = [DocumentPage(page_number=1, text=" ".join(words))]
    config = ChunkingConfig(target_tokens=20, overlap_tokens=5, max_chunks=100)

    chunks = chunk_document(
        document_id=DOC_ID, pages=pages, sections=[section], config=config
    )

    assert len(chunks) > 1
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    # Overlap: the tail of one chunk reappears at the head of the next.
    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    assert first_words[-5:] == second_words[:5]
    # No chunk exceeds the configured target size.
    for chunk in chunks:
        assert len(chunk.text.split()) <= config.target_tokens


def test_coverage_invariant_all_source_words_reachable() -> None:
    words = [f"tok{i}" for i in range(30)]
    section = _section("S", 1, 1)
    pages = [DocumentPage(page_number=1, text=" ".join(words))]
    config = ChunkingConfig(target_tokens=10, overlap_tokens=2, max_chunks=100)

    chunks = chunk_document(
        document_id=DOC_ID, pages=pages, sections=[section], config=config
    )

    covered = set()
    for chunk in chunks:
        covered.update(chunk.text.split())
    assert covered == set(words)


def test_chunk_limit_exceeded_raises() -> None:
    words = [f"w{i}" for i in range(100)]
    pages = [DocumentPage(page_number=1, text=" ".join(words))]
    config = ChunkingConfig(target_tokens=5, overlap_tokens=1, max_chunks=2)

    with pytest.raises(ChunkLimitExceededError):
        chunk_document(document_id=DOC_ID, pages=pages, sections=None, config=config)


def test_all_blank_pages_raise_empty_chunk_output() -> None:
    pages = [
        DocumentPage(page_number=1, text="   "),
        DocumentPage(page_number=2, text=""),
    ]

    with pytest.raises(EmptyChunkOutputError):
        chunk_document(document_id=DOC_ID, pages=pages, sections=None)


def test_invalid_config_rejected() -> None:
    from retrieval.chunking import ChunkingError

    with pytest.raises(ChunkingError):
        ChunkingConfig(target_tokens=10, overlap_tokens=10)
