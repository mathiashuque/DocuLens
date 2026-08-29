"""Deterministic, bounded context construction for grounded single-document
question answering.

Pure domain logic: no HTTP, ORM, or provider dependencies. Takes retrieval's
own ranked search results and turns them into a small, order-preserving,
budget-bounded set of evidence items with honest page/section provenance for
the generation boundary. Whole chunks are included or excluded; a chunk's
text is never partially truncated, so provenance stays exact and citation
validation can trust that any text in a context item's `text` was fully
supplied to the provider.
"""

import uuid
from dataclasses import dataclass

DEFAULT_MAX_CONTEXT_CHUNKS = 5
DEFAULT_MAX_CONTEXT_CHARS = 8000


@dataclass(frozen=True)
class EvidenceContextItem:
    """One opaque chunk reference plus its exact text and honest page/section
    provenance, as handed to the generation provider."""

    chunk_id: uuid.UUID
    chunk_index: int
    text: str
    page_start: int
    page_end: int
    section_title: str | None
    section_path: list[str]


def build_context(
    results: list,
    *,
    max_chunks: int = DEFAULT_MAX_CONTEXT_CHUNKS,
    max_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> list[EvidenceContextItem]:
    """Build a bounded evidence context from ranked search results.

    Preserves retrieval order and stable chunk identity. Stops before
    exceeding `max_chunks` or `max_chars` (cumulative text length); a chunk
    that would push the running total over `max_chars` is excluded entirely
    rather than truncated, so every included item's text is exactly what the
    provider receives and exactly what citation validation checks against.
    """
    if max_chunks <= 0 or max_chars <= 0:
        return []

    items: list[EvidenceContextItem] = []
    used_chars = 0
    for result in results:
        if len(items) >= max_chunks:
            break
        text_len = len(result.text)
        if used_chars + text_len > max_chars:
            continue
        items.append(
            EvidenceContextItem(
                chunk_id=result.chunk_id,
                chunk_index=result.chunk_index,
                text=result.text,
                page_start=result.page_start,
                page_end=result.page_end,
                section_title=result.section_title,
                section_path=result.section_path,
            )
        )
        used_chars += text_len
    return items
