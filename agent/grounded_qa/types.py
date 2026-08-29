"""Typed structured-output contract produced by the grounded-QA provider,
before deterministic citation/evidence validation.

The provider never sees or assigns real chunk identity beyond echoing the
opaque `chunk_id` strings it was given in context; it must not invent page
numbers, chunk IDs, or evidence outside what was supplied.
"""

from typing import Literal

from pydantic import BaseModel, Field

MAX_CITATIONS = 6
MAX_ANSWER_CHARS = 2000


class CitationCandidate(BaseModel):
    """One opaque chunk reference plus the exact page and evidence quote
    the provider claims supports the answer."""

    chunk_id: str = Field(min_length=1, max_length=100)
    page: int = Field(gt=0)
    evidence: str = Field(min_length=1, max_length=2000)


class GroundedAnswerCandidate(BaseModel):
    """The full structured result requested from the provider, for both the
    first pass and the single bounded repair pass. `insufficient_evidence`
    candidates are expected to carry no citations; the application replaces
    their answer text with the stable safe message regardless of what the
    provider wrote."""

    status: Literal["answered", "insufficient_evidence"]
    answer: str = Field(min_length=1, max_length=MAX_ANSWER_CHARS)
    citations: list[CitationCandidate] = Field(
        default_factory=list, max_length=MAX_CITATIONS
    )
