"""Deterministic, structure-aware chunking of persisted page/section text.

Pure domain logic: no HTTP, ORM, database, or provider dependencies. Accepts
already-persisted page text and detected section spans and returns ordered
`Chunk` values with exact page/section provenance.

Page provenance approach
-------------------------
Persisted `DocumentSection.text` is a concatenation of the page lines that
fall within the section's heading span; it does not retain a per-line page
tag once flattened to a single string. Rather than approximate a chunk's
page range by distributing characters proportionally across a section's
broad `page_start..page_end` (which the product brief explicitly forbids),
this module chunks directly from page-labeled source segments: each
document page's own text, annotated with the section (if any) whose
detected span covers that page. A chunk's `page_start`/`page_end` is then
the exact min/max of the physical pages that actually contributed words to
it, never a section's nominal range.

Chunking never merges pages assigned to different sections (or a
sectioned page with an unsectioned page) into one run, so a chunk's section
identity is always unambiguous.
"""

import uuid
from dataclasses import dataclass

from pydantic import BaseModel

from ingestion.models import DocumentPage
from retrieval.tokenizer import estimate_tokens

CHUNKER_VERSION = "v1"

# Chunk index is 0-based: the first chunk of a document is index 0. This
# matches Python's own sequence convention and keeps `chunk_index` usable
# directly as a list offset in the evaluator and API clients.
FIRST_CHUNK_INDEX = 0


class ChunkingError(Exception):
    """Base class for chunking domain errors."""


class ChunkLimitExceededError(ChunkingError):
    """Chunking a document would exceed the configured safeguard."""


class EmptyChunkOutputError(ChunkingError):
    """A document produced no chunks (e.g. entirely blank pages)."""


@dataclass(frozen=True)
class ChunkingConfig:
    """Chunk sizing configuration. Units are the whitespace-token estimate
    from `retrieval.tokenizer.estimate_tokens`, not a provider's BPE tokens.
    """

    target_tokens: int = 800
    overlap_tokens: int = 120
    max_chunks: int = 2000

    def __post_init__(self) -> None:
        if self.target_tokens <= 0:
            raise ChunkingError("target_tokens must be positive.")
        if self.overlap_tokens < 0:
            raise ChunkingError("overlap_tokens must not be negative.")
        if self.overlap_tokens >= self.target_tokens:
            raise ChunkingError("overlap_tokens must be smaller than target_tokens.")
        if self.max_chunks <= 0:
            raise ChunkingError("max_chunks must be positive.")

    @property
    def config_id(self) -> str:
        """A stable string identifying this sizing configuration, recorded
        alongside `CHUNKER_VERSION` on the persisted index for compatibility
        checks and reproducible evaluation."""
        return f"target={self.target_tokens},overlap={self.overlap_tokens}"


DEFAULT_CHUNKING_CONFIG = ChunkingConfig()


class SectionInput(BaseModel):
    """The minimal detected-section shape chunking needs, decoupled from
    the persistence model."""

    id: uuid.UUID
    title: str
    page_start: int
    page_end: int
    section_path: list[str]
    level: int


class Chunk(BaseModel):
    """A deterministic, provenance-complete unit of retrievable text."""

    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    text: str
    page_start: int
    page_end: int
    section_id: uuid.UUID | None
    section_title: str | None
    section_path: list[str]
    token_estimate: int


@dataclass(frozen=True)
class _Word:
    page_number: int
    text: str


def _select_section(
    page_number: int, sections: list[SectionInput]
) -> SectionInput | None:
    """Choose the most specific (deepest, then narrowest) section whose
    detected span covers `page_number`, or None for the page-aware
    fallback. Sections nest by page range in this codebase's detector, so
    depth is a reliable tiebreaker; range width is a secondary tiebreaker
    for same-level candidates."""
    covering = [s for s in sections if s.page_start <= page_number <= s.page_end]
    if not covering:
        return None
    return min(
        covering,
        key=lambda s: (-s.level, s.page_end - s.page_start),
    )


def _build_runs(
    pages: list[DocumentPage], sections: list[SectionInput]
) -> list[tuple[SectionInput | None, list[_Word]]]:
    """Group consecutive non-blank pages sharing the same section
    assignment into runs. A run never spans a section boundary, so no
    chunk derived from it can merge unrelated sections."""
    runs: list[tuple[SectionInput | None, list[_Word]]] = []
    current_section: SectionInput | None = None
    current_words: list[_Word] = []
    started = False

    for page in sorted(pages, key=lambda p: p.page_number):
        if not page.text.strip():
            continue  # blank pages contribute no chunk text
        section = _select_section(page.page_number, sections)
        page_words = [_Word(page.page_number, w) for w in page.text.split()]
        if not page_words:
            continue
        section_key = section.id if section else None
        current_key = current_section.id if current_section else None
        if started and section_key == current_key:
            current_words.extend(page_words)
        else:
            if started:
                runs.append((current_section, current_words))
            current_section = section
            current_words = list(page_words)
            started = True

    if started and current_words:
        runs.append((current_section, current_words))
    return runs


def _split_run(words: list[_Word], config: ChunkingConfig) -> list[list[_Word]]:
    """Split one run's words into overlapping windows, never producing a
    trailing window that only duplicates the previous one."""
    if not words:
        return []
    step = config.target_tokens - config.overlap_tokens
    windows: list[list[_Word]] = []
    start = 0
    n = len(words)
    while start < n:
        end = min(start + config.target_tokens, n)
        windows.append(words[start:end])
        if end >= n:
            break
        start += step
    return windows


def chunk_document(
    *,
    document_id: uuid.UUID,
    pages: list[DocumentPage],
    sections: list[SectionInput] | None = None,
    config: ChunkingConfig = DEFAULT_CHUNKING_CONFIG,
    id_factory: "type[uuid.UUID] | None" = None,
) -> list[Chunk]:
    """Deterministically chunk one document's persisted pages/sections.

    Chunk IDs are freshly generated (random UUID4) on each call; callers
    that need stable identity across calls persist the returned chunks
    once, atomically, as this feature's index service does. Ordering
    (`chunk_index`) is always deterministic for the same inputs and config.
    """
    del id_factory  # reserved for future deterministic-ID injection in tests
    runs = _build_runs(pages, sections or [])

    chunks: list[Chunk] = []
    index = FIRST_CHUNK_INDEX
    for section, words in runs:
        for window in _split_run(words, config):
            if not window:
                continue
            text = " ".join(w.text for w in window)
            page_start = min(w.page_number for w in window)
            page_end = max(w.page_number for w in window)
            chunks.append(
                Chunk(
                    id=uuid.uuid4(),
                    document_id=document_id,
                    chunk_index=index,
                    text=text,
                    page_start=page_start,
                    page_end=page_end,
                    section_id=section.id if section else None,
                    section_title=section.title if section else None,
                    section_path=section.section_path if section else [],
                    token_estimate=estimate_tokens(text),
                )
            )
            index += 1
            if len(chunks) > config.max_chunks:
                raise ChunkLimitExceededError(
                    f"Document {document_id} exceeds the configured "
                    f"maximum of {config.max_chunks} chunks."
                )

    if not chunks:
        raise EmptyChunkOutputError(
            f"Document {document_id} produced no chunkable text."
        )
    return chunks
